"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { HttpAgent } from "@ag-ui/client";
import {
  type SessionsResponse,
  type StatusEntry,
  type BroadcastSendFn,
  BACKEND,
  STORAGE_KEY_PREFIX,
  THREAD_KEY_PREFIX,
  normalizeSessionName,
} from "./types";
import { Sidebar } from "./components/Sidebar";
import { ChatPanel } from "./components/ChatPanel";

export default function Home() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [sessions, setSessions] = useState<SessionsResponse>({ registered: [], acpx: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const [broadcastText, setBroadcastText] = useState("");
  const [broadcasting, setBroadcasting] = useState(false);
  const broadcastFnsRef = useRef<Map<string, BroadcastSendFn>>(new Map());

  const registerBroadcast = useCallback((name: string) => {
    return (send: BroadcastSendFn) => {
      broadcastFnsRef.current.set(name, send);
    };
  }, []);

  const [statusMap, setStatusMap] = useState<Record<string, StatusEntry>>({});
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

  const reconnectSession = useCallback(async (name: string) => {
    try {
      await fetch(`${BACKEND}/sessions/${encodeURIComponent(name)}/reconnect`, {
        method: "POST",
      });
    } catch {}
    fetchStatus();
  }, [fetchStatus]);

  const reconnectCooldowns = useRef<Map<string, number>>(new Map());
  useEffect(() => {
    const now = Date.now();
    for (const [name, entry] of Object.entries(statusMap)) {
      if (entry.health === "disconnected") {
        const lastAttempt = reconnectCooldowns.current.get(name) || 0;
        if (now - lastAttempt > 10_000) {
          reconnectCooldowns.current.set(name, now);
          reconnectSession(name);
        }
      }
    }
  }, [statusMap, reconnectSession]);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch(`${BACKEND}/sessions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SessionsResponse = await res.json();
      setSessions(data);
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
    const set = new Set<string>(sessions.registered.map(normalizeSessionName));
    for (const s of sessions.acpx) if (!s.closed) set.add(normalizeSessionName(s.name));
    return Array.from(set);
  }, [sessions]);

  const defaultCwd = useMemo(() => sessions.projectRoot || "", [sessions.projectRoot]);

  const agentMapRef = useRef<Record<string, HttpAgent>>({});
  const agentMap = useMemo(() => {
    const prev = agentMapRef.current;
    const next: Record<string, HttpAgent> = {};
    for (const name of openSessionNames) {
      next[name] = prev[name] ?? new HttpAgent({
        url: `${BACKEND}/agent/${encodeURIComponent(name)}`,
      });
    }
    agentMapRef.current = next;
    return next;
  }, [openSessionNames]);

  const togglePanel = (name: string) => {
    setOpenPanels((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const closePanel = (name: string) => {
    setOpenPanels((prev) => prev.filter((n) => n !== name));
  };

  const handleCreate = async (data: { name: string; harness: string; cwd: string; llm: string }) => {
    const res = await fetch(`${BACKEND}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({
        name: data.name,
        agent_harness: data.harness,
        working_dir: data.cwd,
        LLM: data.llm || undefined,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    await refresh();
    setOpenPanels((prev) => (prev.includes(data.name) ? prev : [...prev, data.name]));
  };

  const handleDelete = async (name: string) => {
    const normalizedName = normalizeSessionName(name);
    if (!confirm(`Delete session '${name}'? This will remove all message history.`)) return;
    try {
      const res = await fetch(`${BACKEND}/sessions/${encodeURIComponent(normalizedName)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      localStorage.removeItem(STORAGE_KEY_PREFIX + normalizedName);
      localStorage.removeItem(THREAD_KEY_PREFIX + normalizedName);
      closePanel(normalizedName);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const activePanels = openPanels.filter((n) => n in agentMap);

  const [broadcastError, setBroadcastError] = useState<string | null>(null);

  const handleBroadcast = async (text: string) => {
    if (!text || activePanels.length === 0) return;
    setBroadcasting(true);
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
      <Sidebar
        mounted={mounted}
        sessions={sessions}
        openPanels={openPanels}
        statusMap={statusMap}
        activePanels={activePanels}
        openSessionNames={openSessionNames}
        loading={loading}
        error={error}
        defaultCwd={defaultCwd}
        broadcasting={broadcasting}
        broadcastError={broadcastError}
        onRefresh={refresh}
        onTogglePanel={togglePanel}
        onDeleteSession={handleDelete}
        onCreateSession={handleCreate}
        onOpenAll={() => setOpenPanels([...openSessionNames])}
        onCloseAll={() => setOpenPanels([])}
        onBroadcast={handleBroadcast}
      />

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
                status={statusMap[name]?.activity || "idle"}
                health={statusMap[name]?.health || "connected"}
                onClose={() => closePanel(name)}
                onBroadcastReady={registerBroadcast(name)}
                onReconnect={() => reconnectSession(name)}
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
