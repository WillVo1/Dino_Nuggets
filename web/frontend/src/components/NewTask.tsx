import { useEffect, useState } from "react";

import { api } from "../lib/api";
import type { Preset } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (taskId: string) => void;
}

export function NewTask({ open, onClose, onCreated }: Props) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) api.presets().then(setPresets);
  }, [open]);

  if (!open) return null;

  async function submit(preset: string | null, body: string) {
    if (busy || (!preset && !body.trim())) return;
    setBusy(true);
    try {
      const task = await api.createTask(body || preset || "", preset);
      setText("");
      onCreated(task.id);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-[540px] rounded-2xl border border-zinc-800 bg-zinc-950 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 text-base font-semibold">New task</h2>
        <textarea
          autoFocus
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(null, text);
          }}
          placeholder="Describe the task in plain language… (⌘↵ to run)"
          className="w-full resize-none rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-sm outline-none focus:border-zinc-600"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {presets.map((p) => (
            <button
              key={p.key}
              disabled={busy}
              onClick={() => submit(p.key, "")}
              className="rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-zinc-400 hover:text-white">
            Cancel
          </button>
          <button
            disabled={busy || !text.trim()}
            onClick={() => submit(null, text)}
            className="rounded-lg bg-zinc-100 px-4 py-1.5 text-sm font-medium text-zinc-900 disabled:opacity-40"
          >
            {busy ? "Dispatching…" : "Run"}
          </button>
        </div>
      </div>
    </div>
  );
}
