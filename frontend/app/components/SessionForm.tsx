"use client";

import { useState, useEffect } from "react";
import {
  type ModelData,
  BACKEND,
  DEFAULT_HARNESSES,
  normalizeSessionName,
} from "../types";

interface Workspace {
  name: string;
  path: string;
  description: string;
  skills: { name: string; description: string }[];
}

export function SessionForm({
  onSubmit,
  onCancel,
  defaultCwd,
}: {
  onSubmit: (data: { name: string; harness: string; cwd: string; llm: string }) => Promise<void>;
  onCancel: () => void;
  defaultCwd: string;
}) {
  const [formName, setFormName] = useState("");
  const [formHarness, setFormHarness] = useState("opencode");
  const [formCwd, setFormCwd] = useState(defaultCwd);
  const [formLLM, setFormLLM] = useState("");
  const [creating, setCreating] = useState(false);
  const [modelData, setModelData] = useState<ModelData | null>(null);
  const [loadingModels, setLoadingModels] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);

  useEffect(() => {
    fetch(`${BACKEND}/workspaces`)
      .then((r) => r.json())
      .then((data: Workspace[]) => {
        setWorkspaces(data);
        if (data.length > 0 && !formCwd) {
          setFormCwd(data[0].path);
        }
      })
      .catch(() => {});
  }, []);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formCwd.trim()) return;
    setCreating(true);
    try {
      await onSubmit({
        name: normalizeSessionName(formName.trim()),
        harness: formHarness,
        cwd: formCwd.trim(),
        llm: formLLM.trim(),
      });
      setFormName("");
      onCancel();
    } catch {
      // error handled by parent
    } finally {
      setCreating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4 p-3 border border-zinc-200 dark:border-zinc-800 rounded space-y-2">
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
      <select
        value={formCwd}
        onChange={(e) => setFormCwd(e.target.value)}
        className="w-full px-2 py-1 text-sm font-mono border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100"
      >
        {workspaces.map((ws) => (
          <option key={ws.path} value={ws.path}>
            {ws.name === "root" ? "📁 root (generic)" : `🤖 ${ws.name}`}
          </option>
        ))}
      </select>
      {(() => {
        const selected = workspaces.find((ws) => ws.path === formCwd);
        if (!selected || selected.skills.length === 0) return null;
        return (
          <div className="px-2 py-1.5 text-xs bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded">
            <span className="font-medium opacity-70">Skills:</span>
            {selected.skills.map((skill) => (
              <div key={skill.name} className="mt-0.5 pl-2">
                <span className="font-semibold">{skill.name}</span>
                {skill.description && (
                  <span className="opacity-60"> — {skill.description}</span>
                )}
              </div>
            ))}
          </div>
        );
      })()}
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
        className="w-full px-3 py-1.5 text-sm rounded bg-accent text-accent-text hover:bg-accent-hover disabled:opacity-50"
      >
        {creating ? "Creating..." : "Create session"}
      </button>
    </form>
  );
}
