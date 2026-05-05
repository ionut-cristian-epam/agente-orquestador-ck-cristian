"use client";

import { useState } from "react";

export function BroadcastForm({
  activePanelCount,
  onBroadcast,
  broadcasting,
  error,
}: {
  activePanelCount: number;
  onBroadcast: (text: string) => Promise<void>;
  broadcasting: boolean;
  error: string | null;
}) {
  const [broadcastText, setBroadcastText] = useState("");

  const handleSubmit = async () => {
    const text = broadcastText.trim();
    if (!text) return;
    setBroadcastText("");
    await onBroadcast(text);
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      className="mt-auto pt-3 border-t border-zinc-200 dark:border-zinc-800 space-y-2"
    >
      <label className="text-xs font-medium opacity-70">
        Broadcast to {activePanelCount} panels
      </label>
      <textarea
        rows={2}
        placeholder="Send same prompt to all open panels..."
        value={broadcastText}
        onChange={(e) => setBroadcastText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        className="w-full px-2 py-1.5 text-sm border border-zinc-300 dark:border-zinc-700 rounded bg-transparent resize-none"
      />
      <button
        type="submit"
        disabled={broadcasting || !broadcastText.trim()}
        className="w-full px-3 py-1.5 text-sm rounded bg-accent text-accent-text hover:bg-accent-hover disabled:opacity-50"
      >
        {broadcasting ? "Sending..." : "Broadcast (Ctrl+Enter)"}
      </button>
      {error && (
        <div className="p-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 rounded">
          {error}
        </div>
      )}
    </form>
  );
}
