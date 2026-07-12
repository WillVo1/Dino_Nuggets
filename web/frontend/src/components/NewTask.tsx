import { useEffect, useRef, useState } from "react";

import { api } from "../lib/api";
import { MicRecorder } from "../lib/recorder";
import type { Preset } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (taskId: string) => void;
}

type MicState = "idle" | "recording" | "transcribing";

export function NewTask({ open, onClose, onCreated }: Props) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [mic, setMic] = useState<MicState>("idle");
  const [micError, setMicError] = useState<string | null>(null);
  const recorderRef = useRef<MicRecorder | null>(null);

  useEffect(() => {
    if (open) api.presets().then(setPresets);
  }, [open]);

  if (!open) return null;

  async function submit(preset: string | null, body: string) {
    if (busy || (!preset && !body.trim())) return;
    setBusy(true);
    try {
      // display text: user's words, else the preset's friendly label (never the raw key)
      const label = preset ? presets.find((p) => p.key === preset)?.label : "";
      const task = await api.createTask(body.trim() || label || preset || "", preset);
      setText("");
      onCreated(task.id);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  async function toggleMic() {
    setMicError(null);
    if (mic === "idle") {
      try {
        const rec = new MicRecorder();
        await rec.start();
        recorderRef.current = rec;
        setMic("recording");
      } catch {
        setMicError("Microphone unavailable — check browser permissions.");
      }
      return;
    }
    if (mic === "recording") {
      setMic("transcribing");
      try {
        const wav = await recorderRef.current!.stop();
        const { text: transcript } = await api.transcribe(wav);
        if (transcript) {
          setText((prev) => (prev ? `${prev.trimEnd()} ${transcript}` : transcript));
        } else {
          setMicError("Didn't catch that — try again.");
        }
      } catch {
        setMicError("Transcription failed.");
      } finally {
        recorderRef.current = null;
        setMic("idle");
      }
    }
  }

  const micLabel =
    mic === "recording" ? "Stop recording" : mic === "transcribing" ? "Transcribing…" : "Dictate";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-[540px] rounded-2xl border border-zinc-800 bg-zinc-950 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 text-base font-semibold">New task</h2>
        <div className="relative">
          <textarea
            autoFocus
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(null, text);
            }}
            placeholder="Describe the task in plain language… (⌘↵ to run)"
            className="w-full resize-none rounded-lg border border-zinc-800 bg-zinc-900 p-3 pr-12 text-sm outline-none focus:border-zinc-600"
          />
          <button
            type="button"
            onClick={toggleMic}
            disabled={mic === "transcribing"}
            title={micLabel}
            aria-label={micLabel}
            className={`absolute bottom-2.5 right-2.5 flex h-8 w-8 items-center justify-center rounded-full border transition-colors disabled:opacity-60 ${
              mic === "recording"
                ? "animate-pulse border-red-500 bg-red-500/20 text-red-400"
                : "border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-500 hover:text-white"
            }`}
          >
            {mic === "transcribing" ? <Spinner /> : <MicIcon />}
          </button>
        </div>
        {micError && <p className="mt-1.5 text-xs text-red-400">{micError}</p>}
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

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
      <line x1="12" y1="18" x2="12" y2="22" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
