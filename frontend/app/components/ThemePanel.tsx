"use client";

import { ACCENT_PRESETS } from "../types";

export function ThemePanel({
  theme,
  setTheme,
  accent,
  setAccent,
  onClose,
}: {
  theme: string | undefined;
  setTheme: (theme: string) => void;
  accent: string;
  setAccent: (value: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="mb-3 p-3 border border-zinc-200 dark:border-zinc-800 rounded space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Theme Settings</span>
        <button
          onClick={onClose}
          className="text-xs opacity-50 hover:opacity-100"
        >
          ✕
        </button>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium opacity-70">Mode</label>
        <div className="flex gap-1">
          {(["light", "dark", "system"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setTheme(mode)}
              className={`flex-1 px-2 py-1.5 text-xs rounded border transition-colors ${
                theme === mode
                  ? "bg-accent text-accent-text border-accent"
                  : "border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium opacity-70">Accent Color</label>
        <div className="flex gap-2 flex-wrap">
          {ACCENT_PRESETS.map((preset) => (
            <button
              key={preset.value}
              onClick={() => setAccent(preset.value)}
              className={`w-7 h-7 rounded-full border-2 transition-transform ${
                accent === preset.value
                  ? "border-foreground scale-110"
                  : "border-transparent hover:scale-105"
              }`}
              style={{ backgroundColor: preset.swatch }}
              title={preset.name}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
