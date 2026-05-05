"use client";

import {
  type SessionStatus,
  type SessionHealth,
  type AcpxSession,
  STATUS_CONFIG,
  HEALTH_CONFIG,
} from "../types";

export function SessionListItem({
  name,
  meta,
  isPanelOpen,
  status,
  health,
  onToggle,
  onDelete,
}: {
  name: string;
  meta: AcpxSession | undefined;
  isPanelOpen: boolean;
  status: SessionStatus;
  health: SessionHealth;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const statusCfg = STATUS_CONFIG[status];
  const healthCfg = HEALTH_CONFIG[health];
  const dotColor = health !== "connected" ? healthCfg.color : statusCfg.color;
  const dotPulse = health !== "connected" ? healthCfg.pulse : statusCfg.pulse;

  return (
    <li
      className={`p-2 rounded text-sm cursor-pointer flex items-start justify-between gap-2 ${
        isPanelOpen
          ? "bg-accent text-accent-text"
          : "hover:bg-zinc-100 dark:hover:bg-zinc-900"
      }`}
      onClick={onToggle}
    >
      <div className="min-w-0 flex-1">
        <div className="font-medium truncate flex items-center gap-1.5">
          <span
            className={`inline-block w-2 h-2 rounded-full shrink-0 ${dotColor} ${dotPulse ? "animate-pulse" : ""}`}
            title={health !== "connected" ? healthCfg.label : statusCfg.label}
          />
          {name}
          {health === "disconnected" && (
            <span className="text-xs font-normal text-red-500 ml-1">Disconnected</span>
          )}
          {health === "reconnecting" && (
            <span className="text-xs font-normal text-amber-500 ml-1">Reconnecting...</span>
          )}
          {health === "connected" && status !== "idle" && (
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
          onDelete();
        }}
        className="text-xs opacity-50 hover:opacity-100 px-1"
        title="Close session"
      >
        ✕
      </button>
    </li>
  );
}
