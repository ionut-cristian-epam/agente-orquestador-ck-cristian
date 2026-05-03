"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import {
  CopilotKitProvider,
  CopilotChat,
  CopilotChatConfigurationProvider,
  useCopilotChatConfiguration,
  useAgent,
  useCopilotKit,
} from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type SessionStatus = "idle" | "thinking" | "tool_use" | "responding";

const STATUS_CONFIG: Record<SessionStatus, { label: string; color: string; pulse: boolean }> = {
  idle:       { label: "Idle",       color: "bg-zinc-400", pulse: false },
  thinking:   { label: "Thinking",   color: "bg-yellow-400", pulse: true },
  tool_use:   { label: "Tool use",   color: "bg-blue-400", pulse: true },
  responding: { label: "Responding", color: "bg-green-400", pulse: true },
};

type AcpxSession = {
  name: string;
  cwd: string;
  closed: boolean;
  lastUsedAt: string | null;
};

type SessionsResponse = {
  projectRoot?: string;
  registered: string[];
  acpx: AcpxSession[];
};

const DEFAULT_HARNESSES = [
  "opencode",
  "claude",
  "codex",
  "gemini",
  "cursor",
  "copilot",
];

type ModelData = { groups: Record<string, string[]>; default: string };

/* ------------------------------------------------------------------ */
/*  Message persistence — saves/restores chat history per session      */
/* ------------------------------------------------------------------ */

const STORAGE_KEY_PREFIX = "chat_messages:";

/**
 * Wrap an HttpAgent so every clone it produces:
 *  - restores messages from localStorage instead of starting empty
 *  - persists messages to localStorage on every change
 */
function makePersistentAgent(base: HttpAgent, sessionName: string): HttpAgent {
  const key = STORAGE_KEY_PREFIX + sessionName;
  const origClone = base.clone.bind(base);

  base.clone = function () {
    const clone = origClone();

    // --- restore: intercept the setMessages([]) that cloneForThread fires ---
    const protoSetMessages = Object.getPrototypeOf(clone).setMessages.bind(clone);
    let interceptClear = true;
    clone.setMessages = function (msgs: any[]) {
      if (interceptClear && msgs.length === 0) {
        interceptClear = false;
        try {
          const stored = localStorage.getItem(key);
          if (stored) {
            const restored = JSON.parse(stored);
            if (Array.isArray(restored) && restored.length > 0) {
              protoSetMessages(restored);
              return;
            }
          }
        } catch {}
      }
      interceptClear = false;
      protoSetMessages(msgs);
    };

    // --- save: property setter catches direct `this.messages = …` ---
    let _msgs = clone.messages;
    const save = () => {
      try {
        if (_msgs.length > 0) localStorage.setItem(key, JSON.stringify(_msgs));
      } catch {}
    };
    Object.defineProperty(clone, "messages", {
      get: () => _msgs,
      set: (v) => { _msgs = v; save(); },
      configurable: true,
      enumerable: true,
    });

    // --- save: also catch in-place mutations via addMessage/addMessages ---
    const protoAdd = Object.getPrototypeOf(clone).addMessage.bind(clone);
    clone.addMessage = function (m: any) { protoAdd(m); save(); };
    const protoAdds = Object.getPrototypeOf(clone).addMessages.bind(clone);
    clone.addMessages = function (m: any[]) { protoAdds(m); save(); };

    return clone;
  };

  return base;
}

/* ------------------------------------------------------------------ */
/*  Broadcast — inject a prompt into a CopilotChat panel               */
/* ------------------------------------------------------------------ */

type BroadcastSendFn = (text: string) => Promise<void>;

const THREAD_KEY_PREFIX = "chat_thread:";

function getOrCreateThreadId(sessionName: string): string {
  const key = THREAD_KEY_PREFIX + sessionName;
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(key, id);
  return id;
}

function BroadcastReceiver({
  onRegister,
}: {
  onRegister: (send: BroadcastSendFn) => void;
}) {
  const chatCfg = useCopilotChatConfiguration();
  const { agent } = useAgent({
    agentId: chatCfg?.agentId,
    threadId: chatCfg?.threadId,
  });
  const { copilotkit } = useCopilotKit();
  const agentRef = useRef(agent);
  const ckRef = useRef(copilotkit);

  useEffect(() => { agentRef.current = agent; }, [agent]);
  useEffect(() => { ckRef.current = copilotkit; }, [copilotkit]);

  useEffect(() => {
    onRegister(async (text: string) => {
      const a = agentRef.current;
      a.addMessage({
        id: crypto.randomUUID(),
        role: "user" as const,
        content: text,
      });
      await ckRef.current.runAgent({ agent: a });
    });
  }, [onRegister]);

  return null;
}

/* ------------------------------------------------------------------ */
/*  Clear chat — wipe agent messages + localStorage                    */
/* ------------------------------------------------------------------ */

function ClearChatButton({ sessionName }: { sessionName: string }) {
  const chatCfg = useCopilotChatConfiguration();
  const { agent } = useAgent({
    agentId: chatCfg?.agentId,
    threadId: chatCfg?.threadId,
  });

  const handleClear = () => {
    agent.setMessages([]);
    localStorage.removeItem(STORAGE_KEY_PREFIX + sessionName);
  };

  return (
    <button
      onClick={handleClear}
      className="text-xs opacity-50 hover:opacity-100 px-1.5 py-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800"
      title="Clear chat history"
    >
      Clear
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Chat panel — each has its own CopilotKitProvider so they stream    */
/*  independently from different backend sessions.                     */
/* ------------------------------------------------------------------ */

function ChatPanel({
  name,
  agent,
  status,
  onClose,
  onBroadcastReady,
}: {
  name: string;
  agent: HttpAgent;
  status: SessionStatus;
  onClose: () => void;
  onBroadcastReady?: (send: BroadcastSendFn) => void;
}) {
  const persistentAgent = useMemo(() => makePersistentAgent(agent, name), [agent, name]);
  const agents = useMemo(() => ({ [name]: persistentAgent }), [name, persistentAgent]);
  const cfg = STATUS_CONFIG[status];
  const threadId = useMemo(() => getOrCreateThreadId(name), [name]);

  return (
    <CopilotKitProvider key={name} agents__unsafe_dev_only={agents}>
      <CopilotChatConfigurationProvider agentId={name} threadId={threadId}>
        {onBroadcastReady && (
          <BroadcastReceiver onRegister={onBroadcastReady} />
        )}
        <div className="flex flex-col h-full min-w-0 overflow-hidden border-r last:border-r-0 border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 shrink-0">
            <span className="font-mono text-sm font-medium truncate flex items-center gap-1.5">
              <span
                className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.color} ${cfg.pulse ? "animate-pulse" : ""}`}
                title={cfg.label}
              />
              {name}
              {status !== "idle" && (
                <span className="text-xs font-normal opacity-60 ml-1">{cfg.label}</span>
              )}
            </span>
            <span className="flex items-center gap-1">
              <ClearChatButton sessionName={name} />
              <button
                onClick={onClose}
                className="text-xs opacity-50 hover:opacity-100 px-1.5 py-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-800"
                title="Close panel"
              >
                ✕
              </button>
            </span>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto">
            <CopilotChat
              agentId={name}
              labels={{ chatInputPlaceholder: `Message ${name}...` }}
            />
          </div>
        </div>
      </CopilotChatConfigurationProvider>
    </CopilotKitProvider>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export default function Home() {
  const [sessions, setSessions] = useState<SessionsResponse>({ registered: [], acpx: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Open panels — ordered list of session names currently displayed
  const [openPanels, setOpenPanels] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem("openPanels");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("openPanels", JSON.stringify(openPanels));
  }, [openPanels]);

  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formHarness, setFormHarness] = useState("opencode");
  const [formCwd, setFormCwd] = useState("");
  const [formLLM, setFormLLM] = useState("");
  const [creating, setCreating] = useState(false);
  const [modelData, setModelData] = useState<ModelData | null>(null);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadingModels(true);
    fetch(`${BACKEND}/models/${encodeURIComponent(formHarness)}`)
      .then((r) => r.json())
      .then((data: ModelData) => {
        if (cancelled) return;
        setModelData(data);
        setFormLLM((cur) => {
          const allModels = Object.values(data.groups).flat();
          if (cur && allModels.includes(cur)) return cur;
          return data.default || "";
        });
      })
      .catch(() => { if (!cancelled) setModelData(null); })
      .finally(() => { if (!cancelled) setLoadingModels(false); });
    return () => { cancelled = true; };
  }, [formHarness]);

  // Broadcast prompt
  const [broadcastText, setBroadcastText] = useState("");
  const [broadcasting, setBroadcasting] = useState(false);
  const broadcastFnsRef = useRef<Map<string, BroadcastSendFn>>(new Map());

  const registerBroadcast = useCallback((name: string) => {
    return (send: BroadcastSendFn) => {
      broadcastFnsRef.current.set(name, send);
    };
  }, []);


  // Session status polling
  const [statusMap, setStatusMap] = useState<Record<string, SessionStatus>>({});
  const statusIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND}/sessions/status`);
      if (res.ok) setStatusMap(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchStatus();
    statusIntervalRef.current = setInterval(fetchStatus, 1500);
    return () => {
      if (statusIntervalRef.current) clearInterval(statusIntervalRef.current);
    };
  }, [fetchStatus]);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch(`${BACKEND}/sessions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SessionsResponse = await res.json();
      setSessions(data);
      if (data.projectRoot) {
        setFormCwd((cur) => cur || data.projectRoot!);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const openSessionNames = useMemo(() => {
    const set = new Set<string>(sessions.registered);
    for (const s of sessions.acpx) if (!s.closed) set.add(s.name);
    return Array.from(set);
  }, [sessions]);

  // Build HttpAgent instances for all known sessions
  const agentMap = useMemo(() => {
    const map: Record<string, HttpAgent> = {};
    for (const name of openSessionNames) {
      map[name] = new HttpAgent({ url: `${BACKEND}/agent/${encodeURIComponent(name)}` });
    }
    return map;
  }, [openSessionNames]);

  // Toggle a session panel open/closed
  const togglePanel = (name: string) => {
    setOpenPanels((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const closePanel = (name: string) => {
    setOpenPanels((prev) => prev.filter((n) => n !== name));
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formCwd.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${BACKEND}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formName.trim(),
          agent_harness: formHarness,
          working_dir: formCwd.trim(),
          LLM: formLLM.trim() || undefined,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const newName = formName.trim();
      setShowForm(false);
      setFormName("");
      await refresh();
      // Auto-open the new session panel
      setOpenPanels((prev) => (prev.includes(newName) ? prev : [...prev, newName]));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete session '${name}'? This will remove all message history.`)) return;
    try {
      const res = await fetch(`${BACKEND}/sessions/${encodeURIComponent(name)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      localStorage.removeItem(STORAGE_KEY_PREFIX + name);
      localStorage.removeItem(THREAD_KEY_PREFIX + name);
      closePanel(name);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  // Filter panels to only those that still exist
  const activePanels = openPanels.filter((n) => n in agentMap);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [broadcastError, setBroadcastError] = useState<string | null>(null);

  const handleBroadcast = async () => {
    const text = broadcastText.trim();
    if (!text || activePanels.length === 0) return;
    setBroadcasting(true);
    setBroadcastText("");
    setBroadcastError(null);
    try {
      const fns = activePanels.map((name) => ({
        name,
        fn: broadcastFnsRef.current.get(name),
      }));
      const missing = fns.filter((f) => !f.fn).map((f) => f.name);
      if (missing.length > 0) {
        setBroadcastError(`No broadcast handler for: ${missing.join(", ")}`);
        setBroadcasting(false);
        return;
      }
      const results = await Promise.allSettled(
        fns.map(({ name, fn }) =>
          fn!(text).catch((e: unknown) => {
            throw new Error(`${name}: ${e instanceof Error ? e.message : String(e)}`);
          })
        )
      );
      const errors = results
        .filter((r): r is PromiseRejectedResult => r.status === "rejected")
        .map((r) => r.reason?.message || String(r.reason));
      if (errors.length > 0) setBroadcastError(errors.join("; "));
    } catch (e) {
      setBroadcastError(e instanceof Error ? e.message : String(e));
    } finally {
      setBroadcasting(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* ---- Sidebar ---- */}
      <aside
        className={`border-r border-zinc-200 dark:border-zinc-800 overflow-y-auto flex flex-col shrink-0 transition-[width] duration-200 ${
          sidebarOpen ? "w-[360px] p-5" : "w-10 py-2 px-1"
        }`}
      >
        <div className={`flex items-center mb-3 ${sidebarOpen ? "justify-between" : "justify-center"}`}>
          {sidebarOpen && <h1 className="text-lg font-semibold whitespace-nowrap">Agent Sessions</h1>}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="px-2 py-1 text-sm rounded hover:bg-zinc-200 dark:hover:bg-zinc-800 shrink-0"
            title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
          >
            {sidebarOpen ? "«" : "»"}
          </button>
        </div>

        {!sidebarOpen ? null : <>
        <div className="flex gap-2 mb-3">
          <button
            onClick={refresh}
            className="px-3 py-1.5 text-sm rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-3 py-1.5 text-sm rounded bg-black text-white dark:bg-white dark:text-black hover:opacity-80"
          >
            {showForm ? "Cancel" : "+ New"}
          </button>
        </div>

        {error && (
          <div className="mb-3 p-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 rounded">
            {error}
          </div>
        )}

        {showForm && (
          <form onSubmit={handleCreate} className="mb-4 p-3 border border-zinc-200 dark:border-zinc-800 rounded space-y-2">
            <input
              required
              placeholder="session name"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-zinc-300 dark:border-zinc-700 rounded bg-transparent"
            />
            <select
              value={formHarness}
              onChange={(e) => setFormHarness(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100"
            >
              {DEFAULT_HARNESSES.map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
            <input
              required
              placeholder="working_dir (absolute path)"
              value={formCwd}
              onChange={(e) => setFormCwd(e.target.value)}
              className="w-full px-2 py-1 text-sm font-mono border border-zinc-300 dark:border-zinc-700 rounded bg-transparent"
            />
            {modelData && Object.keys(modelData.groups).length > 0 ? (
              <select
                value={formLLM}
                onChange={(e) => setFormLLM(e.target.value)}
                disabled={loadingModels}
                className="w-full px-2 py-1 text-sm font-mono border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 disabled:opacity-50"
              >
                <option value="">{loadingModels ? "Loading..." : "— Select model —"}</option>
                {Object.entries(modelData.groups).map(([group, models]) =>
                  Object.keys(modelData.groups).length > 1 ? (
                    <optgroup key={group} label={group}>
                      {models.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </optgroup>
                  ) : (
                    models.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))
                  )
                )}
              </select>
            ) : (
              <input
                placeholder="LLM (optional)"
                value={formLLM}
                onChange={(e) => setFormLLM(e.target.value)}
                className="w-full px-2 py-1 text-sm font-mono border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100"
              />
            )}
            <button
              type="submit"
              disabled={creating}
              className="w-full px-3 py-1.5 text-sm rounded bg-black text-white dark:bg-white dark:text-black hover:opacity-80 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create session"}
            </button>
          </form>
        )}

        {loading ? (
          <p className="text-sm text-zinc-500">Loading...</p>
        ) : openSessionNames.length === 0 ? (
          <p className="text-sm text-zinc-500">No open sessions. Click + New.</p>
        ) : (
          <ul className="space-y-1">
            {openSessionNames.map((name) => {
              const meta = sessions.acpx.find((s) => s.name === name);
              const isPanelOpen = openPanels.includes(name);
              const status: SessionStatus = statusMap[name] || "idle";
              const statusCfg = STATUS_CONFIG[status];
              return (
                <li
                  key={name}
                  className={`p-2 rounded text-sm cursor-pointer flex items-start justify-between gap-2 ${
                    isPanelOpen
                      ? "bg-black text-white dark:bg-white dark:text-black"
                      : "hover:bg-zinc-100 dark:hover:bg-zinc-900"
                  }`}
                  onClick={() => togglePanel(name)}
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate flex items-center gap-1.5">
                      <span
                        className={`inline-block w-2 h-2 rounded-full shrink-0 ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`}
                        title={statusCfg.label}
                      />
                      {name}
                      {status !== "idle" && (
                        <span className="text-xs font-normal opacity-50 ml-1">{statusCfg.label}</span>
                      )}
                    </div>
                    {meta?.cwd && (
                      <div className="text-xs opacity-70 truncate font-mono ml-3.5">{meta.cwd}</div>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(name);
                    }}
                    className="text-xs opacity-50 hover:opacity-100 px-1"
                    title="Close session"
                  >
                    ✕
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {/* Open all / Close all */}
        {openSessionNames.length > 1 && (
          <div className="flex gap-2 mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
            <button
              onClick={() => setOpenPanels([...openSessionNames])}
              className="flex-1 px-2 py-1 text-xs rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
            >
              Open all
            </button>
            <button
              onClick={() => setOpenPanels([])}
              className="flex-1 px-2 py-1 text-xs rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
            >
              Close all
            </button>
          </div>
        )}

        {/* Broadcast prompt */}
        {activePanels.length > 1 && (
          <form
            onSubmit={(e) => { e.preventDefault(); handleBroadcast(); }}
            className="mt-auto pt-3 border-t border-zinc-200 dark:border-zinc-800 space-y-2"
          >
            <label className="text-xs font-medium opacity-70">
              Broadcast to {activePanels.length} panels
            </label>
            <textarea
              rows={2}
              placeholder="Send same prompt to all open panels..."
              value={broadcastText}
              onChange={(e) => setBroadcastText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  handleBroadcast();
                }
              }}
              className="w-full px-2 py-1.5 text-sm border border-zinc-300 dark:border-zinc-700 rounded bg-transparent resize-none"
            />
            <button
              type="submit"
              disabled={broadcasting || !broadcastText.trim()}
              className="w-full px-3 py-1.5 text-sm rounded bg-black text-white dark:bg-white dark:text-black hover:opacity-80 disabled:opacity-50"
            >
              {broadcasting ? "Sending..." : "Broadcast (Ctrl+Enter)"}
            </button>
            {broadcastError && (
              <div className="p-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 rounded">
                {broadcastError}
              </div>
            )}
          </form>
        )}
        </>}
      </aside>

      {/* ---- Multi-panel chat area ---- */}
      <main className="flex flex-col min-h-0 min-w-0 flex-1 overflow-hidden">
        {activePanels.length > 0 ? (
          <div
            className="flex-1 grid min-h-0 overflow-hidden"
            style={{
              gridTemplateColumns: `repeat(${activePanels.length}, minmax(0, 1fr))`,
            }}
          >
            {activePanels.map((name) => (
              <ChatPanel
                key={name}
                name={name}
                agent={agentMap[name]}
                status={statusMap[name] || "idle"}
                onClose={() => closePanel(name)}
                onBroadcastReady={registerBroadcast(name)}
              />
            ))}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500">
            <div className="text-center space-y-2">
              <p className="text-sm">Click a session in the sidebar to open a chat panel.</p>
              <p className="text-xs opacity-60">Open multiple sessions to chat side by side.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
