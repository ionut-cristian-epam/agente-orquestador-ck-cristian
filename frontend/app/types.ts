export const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export const ACCENT_PRESETS = [
  { name: "Blue",    value: "blue",    swatch: "#2563eb" },
  { name: "Violet",  value: "violet",  swatch: "#7c3aed" },
  { name: "Rose",    value: "rose",    swatch: "#e11d48" },
  { name: "Amber",   value: "amber",   swatch: "#d97706" },
  { name: "Emerald", value: "emerald", swatch: "#059669" },
  { name: "Cyan",    value: "cyan",    swatch: "#0891b2" },
] as const;

export function normalizeSessionName(name: string): string {
  return name.normalize("NFC");
}

export type SessionStatus = "idle" | "thinking" | "tool_use" | "responding";
export type SessionHealth = "connected" | "disconnected" | "reconnecting";

export const STATUS_CONFIG: Record<SessionStatus, { label: string; color: string; pulse: boolean }> = {
  idle:       { label: "Idle",       color: "bg-zinc-400", pulse: false },
  thinking:   { label: "Thinking",   color: "bg-yellow-400", pulse: true },
  tool_use:   { label: "Tool use",   color: "bg-blue-400", pulse: true },
  responding: { label: "Responding", color: "bg-green-400", pulse: true },
};

export const HEALTH_CONFIG: Record<SessionHealth, { label: string; color: string; pulse: boolean }> = {
  connected:    { label: "",              color: "",             pulse: false },
  disconnected: { label: "Disconnected",  color: "bg-red-500",  pulse: false },
  reconnecting: { label: "Reconnecting",  color: "bg-amber-400", pulse: true },
};

export type AcpxSession = {
  name: string;
  cwd: string;
  closed: boolean;
  lastUsedAt: string | null;
};

export type SessionsResponse = {
  projectRoot?: string;
  registered: string[];
  acpx: AcpxSession[];
};

export const DEFAULT_HARNESSES = [
  "opencode",
  "claude",
  "codex",
  "gemini",
  "cursor",
  "copilot",
];

export type ModelData = { groups: Record<string, string[]>; default: string };

export const STORAGE_KEY_PREFIX = "chat_messages:";
export const THREAD_KEY_PREFIX = "chat_thread:";

export type HistoryEntry = {
  role: string;
  content: string;
  thinking?: string;
};

export type StatusEntry = { activity: SessionStatus; health: SessionHealth };

export type SessionMetrics = {
  turns: number;
  total_text_chars: number;
  total_thinking_chars: number;
  total_tool_calls: number;
  total_response_time_ms: number;
  last_response_time_ms: number;
  avg_response_time_ms: number;
  last_tool_calls: number;
  last_text_chars: number;
  last_thinking_chars: number;
};

export type BroadcastSendFn = (text: string) => Promise<void>;

export function getOrCreateThreadId(sessionName: string): string {
  sessionName = normalizeSessionName(sessionName);
  const key = THREAD_KEY_PREFIX + sessionName;
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(key, id);
  return id;
}
