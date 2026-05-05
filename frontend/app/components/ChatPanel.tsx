"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  CopilotKitProvider,
  CopilotChat,
  CopilotChatConfigurationProvider,
  useCopilotChatConfiguration,
  useAgent,
  useCopilotKit,
} from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";
import {
  type SessionStatus,
  type SessionHealth,
  type SessionMetrics,
  type BroadcastSendFn,
  type HistoryEntry,
  STATUS_CONFIG,
  HEALTH_CONFIG,
  BACKEND,
  STORAGE_KEY_PREFIX,
  normalizeSessionName,
  getOrCreateThreadId,
} from "../types";

function HistoryLoader({ sessionName }: { sessionName: string }) {
  const chatCfg = useCopilotChatConfiguration();
  const { agent } = useAgent({
    agentId: chatCfg?.agentId,
    threadId: chatCfg?.threadId,
  });
  const loaded = useRef(false);
  const normalizedName = normalizeSessionName(sessionName);

  useEffect(() => {
    if (loaded.current) return;
    if (agent.messages.length > 0) {
      loaded.current = true;
      return;
    }
    loaded.current = true;

    fetch(`${BACKEND}/sessions/${encodeURIComponent(normalizedName)}/history`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data?.entries?.length) return;
        const msgs: { id: string; role: "user" | "assistant" | "reasoning"; content: string }[] = [];
        (data.entries as HistoryEntry[]).forEach((e, i) => {
          if (e.role === "assistant") {
            if (e.thinking) {
              msgs.push({
                id: `history-${normalizedName}-${i}-think`,
                role: "reasoning",
                content: e.thinking,
              });
            }
            msgs.push({
              id: `history-${normalizedName}-${i}`,
              role: "assistant",
              content: e.content || "",
            });
          } else {
            msgs.push({
              id: `history-${normalizedName}-${i}`,
              role: "user",
              content: e.content || "",
            });
          }
        });
        if (msgs.length > 0 && agent.messages.length === 0) {
          agent.setMessages(msgs);
        }
      })
      .catch(() => {});
  }, [agent, normalizedName]);

  return null;
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

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m${rem}s`;
}

function formatChars(n: number): string {
  if (n < 1000) return `${n}`;
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`;
  return `${(n / 1_000_000).toFixed(1)}M`;
}

function MetricPill({ icon, label, value, detail }: { icon: string; label: string; value: string; detail?: string }) {
  return (
    <span
      title={detail || `${label}: ${value}`}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/80"
    >
      <span>{icon}</span>
      <span className="text-zinc-400 dark:text-zinc-500">{label}</span>
      <span className="text-zinc-700 dark:text-zinc-300 font-semibold">{value}</span>
    </span>
  );
}

function MetricsBar({ metrics }: { metrics: SessionMetrics | undefined }) {
  if (!metrics || metrics.turns === 0) return null;

  return (
    <div className="flex items-center gap-1.5 px-3 py-1 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 text-[11px] text-zinc-500 dark:text-zinc-400 font-mono shrink-0 overflow-x-auto">
      <MetricPill
        icon="💬"
        label="Turnos"
        value={String(metrics.turns)}
      />
      <MetricPill
        icon="🔧"
        label="Herram."
        value={String(metrics.total_tool_calls)}
        detail={`Llamadas a herramientas: ${metrics.total_tool_calls} (último turno: ${metrics.last_tool_calls})`}
      />
      <MetricPill
        icon="⏱"
        label="Prom."
        value={formatDuration(metrics.avg_response_time_ms)}
        detail={`Tiempo promedio: ${formatDuration(metrics.avg_response_time_ms)} · Último: ${formatDuration(metrics.last_response_time_ms)} · Total: ${formatDuration(metrics.total_response_time_ms)}`}
      />
      <MetricPill
        icon="📝"
        label="Salida"
        value={formatChars(metrics.total_text_chars)}
        detail={`Texto generado: ${metrics.total_text_chars.toLocaleString()} chars (último turno: ${metrics.last_text_chars.toLocaleString()})`}
      />
      {metrics.total_thinking_chars > 0 && (
        <MetricPill
          icon="🧠"
          label="Pensam."
          value={formatChars(metrics.total_thinking_chars)}
          detail={`Pensamiento total: ${metrics.total_thinking_chars.toLocaleString()} chars (último turno: ${metrics.last_thinking_chars.toLocaleString()})`}
        />
      )}
    </div>
  );
}

function ClearChatButton({ sessionName }: { sessionName: string }) {
  const chatCfg = useCopilotChatConfiguration();
  const { agent } = useAgent({
    agentId: chatCfg?.agentId,
    threadId: chatCfg?.threadId,
  });
  const normalizedName = normalizeSessionName(sessionName);

  const handleClear = () => {
    agent.setMessages([]);
    localStorage.removeItem(STORAGE_KEY_PREFIX + normalizedName);
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

export function ChatPanel({
  name,
  agent,
  status,
  health,
  metrics,
  onClose,
  onBroadcastReady,
  onReconnect,
}: {
  name: string;
  agent: HttpAgent;
  status: SessionStatus;
  health: SessionHealth;
  metrics?: SessionMetrics;
  onClose: () => void;
  onBroadcastReady?: (send: BroadcastSendFn) => void;
  onReconnect: () => void;
}) {
  const agents = useMemo(() => ({ [name]: agent }), [name, agent]);
  const cfg = STATUS_CONFIG[status];
  const healthCfg = HEALTH_CONFIG[health];
  const threadId = useMemo(() => getOrCreateThreadId(name), [name]);

  const dotColor = health !== "connected" ? healthCfg.color : cfg.color;
  const dotPulse = health !== "connected" ? healthCfg.pulse : cfg.pulse;

  return (
    <CopilotKitProvider key={name} agents__unsafe_dev_only={agents}>
      <CopilotChatConfigurationProvider agentId={name} threadId={threadId}>
        <HistoryLoader sessionName={name} />
        {onBroadcastReady && (
          <BroadcastReceiver onRegister={onBroadcastReady} />
        )}
        <div className="flex flex-col h-full min-w-0 overflow-hidden border-r last:border-r-0 border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 shrink-0">
            <span className="font-mono text-sm font-medium truncate flex items-center gap-1.5">
              <span
                className={`inline-block w-2 h-2 rounded-full shrink-0 ${dotColor} ${dotPulse ? "animate-pulse" : ""}`}
                title={health !== "connected" ? healthCfg.label : cfg.label}
              />
              {name}
              {health === "disconnected" && (
                <span className="text-xs font-normal text-red-500 ml-1 flex items-center gap-1">
                  Disconnected
                  <button
                    onClick={(e) => { e.stopPropagation(); onReconnect(); }}
                    className="underline hover:no-underline"
                  >
                    Retry
                  </button>
                </span>
              )}
              {health === "reconnecting" && (
                <span className="text-xs font-normal text-amber-500 ml-1">
                  Reconnecting...
                </span>
              )}
              {health === "connected" && status !== "idle" && (
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
          <MetricsBar metrics={metrics} />
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
