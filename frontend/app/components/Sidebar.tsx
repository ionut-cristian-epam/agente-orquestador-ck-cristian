"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { useAccentColor } from "../hooks";
import {
  type SessionStatus,
  type SessionHealth,
  type AcpxSession,
  type StatusEntry,
  normalizeSessionName,
} from "../types";
import { ThemePanel } from "./ThemePanel";
import { SessionForm } from "./SessionForm";
import { SessionListItem } from "./SessionListItem";
import { BroadcastForm } from "./BroadcastForm";

export function Sidebar({
  mounted,
  sessions,
  openPanels,
  statusMap,
  activePanels,
  loading,
  error,
  defaultCwd,
  broadcasting,
  broadcastError,
  onRefresh,
  onTogglePanel,
  onDeleteSession,
  onCreateSession,
  onOpenAll,
  onCloseAll,
  onBroadcast,
  openSessionNames,
}: {
  mounted: boolean;
  sessions: { acpx: AcpxSession[] };
  openPanels: string[];
  statusMap: Record<string, StatusEntry>;
  activePanels: string[];
  loading: boolean;
  error: string | null;
  defaultCwd: string;
  broadcasting: boolean;
  broadcastError: string | null;
  onRefresh: () => void;
  onTogglePanel: (name: string) => void;
  onDeleteSession: (name: string) => void;
  onCreateSession: (data: { name: string; harness: string; cwd: string; llm: string }) => Promise<void>;
  onOpenAll: () => void;
  onCloseAll: () => void;
  onBroadcast: (text: string) => Promise<void>;
  openSessionNames: string[];
}) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [accent, setAccent] = useAccentColor();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showThemePanel, setShowThemePanel] = useState(false);

  return (
    <aside
      className={`border-r border-zinc-200 dark:border-zinc-800 overflow-y-auto flex flex-col shrink-0 transition-[width] duration-200 ${
        sidebarOpen ? "w-[360px] p-5" : "w-10 py-2 px-1"
      }`}
    >
      <div className={`flex items-center mb-3 ${sidebarOpen ? "justify-between" : "justify-center"}`}>
        {sidebarOpen && <h1 className="text-lg font-semibold whitespace-nowrap">Agent Sessions</h1>}
        <span className="flex items-center gap-1">
          {mounted && sidebarOpen && (
            <>
              <button
                onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
                className="px-2 py-1 text-sm rounded hover:bg-zinc-200 dark:hover:bg-zinc-800 shrink-0"
                title={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}
              >
                {resolvedTheme === "dark" ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                )}
              </button>
              <button
                onClick={() => setShowThemePanel((v) => !v)}
                className="px-2 py-1 text-sm rounded hover:bg-zinc-200 dark:hover:bg-zinc-800 shrink-0"
                title="Theme settings"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              </button>
            </>
          )}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="px-2 py-1 text-sm rounded hover:bg-zinc-200 dark:hover:bg-zinc-800 shrink-0"
            title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
          >
            {sidebarOpen ? "«" : "»"}
          </button>
        </span>
      </div>

      {showThemePanel && sidebarOpen && mounted && (
        <ThemePanel
          theme={theme}
          setTheme={setTheme}
          accent={accent}
          setAccent={setAccent}
          onClose={() => setShowThemePanel(false)}
        />
      )}

      {!sidebarOpen ? null : <>
      <div className="flex gap-2 mb-3">
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 text-sm rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
        >
          Refresh
        </button>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-3 py-1.5 text-sm rounded bg-accent text-accent-text hover:bg-accent-hover"
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
        <SessionForm
          onSubmit={onCreateSession}
          onCancel={() => setShowForm(false)}
          defaultCwd={defaultCwd}
        />
      )}

      {loading ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : openSessionNames.length === 0 ? (
        <p className="text-sm text-zinc-500">No open sessions. Click + New.</p>
      ) : (
        <ul className="space-y-1">
          {openSessionNames.map((name: string) => {
            const meta = sessions.acpx.find((s) => normalizeSessionName(s.name) === name);
            const isPanelOpen = openPanels.includes(name);
            const status: SessionStatus = statusMap[name]?.activity || "idle";
            const health: SessionHealth = statusMap[name]?.health || "connected";
            return (
              <SessionListItem
                key={name}
                name={name}
                meta={meta}
                isPanelOpen={isPanelOpen}
                status={status}
                health={health}
                onToggle={() => onTogglePanel(name)}
                onDelete={() => onDeleteSession(name)}
              />
            );
          })}
        </ul>
      )}

      {openSessionNames.length > 1 && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
          <button
            onClick={onOpenAll}
            className="flex-1 px-2 py-1 text-xs rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            Open all
          </button>
          <button
            onClick={onCloseAll}
            className="flex-1 px-2 py-1 text-xs rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            Close all
          </button>
        </div>
      )}

      {activePanels.length > 1 && (
        <BroadcastForm
          activePanelCount={activePanels.length}
          onBroadcast={onBroadcast}
          broadcasting={broadcasting}
          error={broadcastError}
        />
      )}
      </>}
    </aside>
  );
}
