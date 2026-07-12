import type { TaskStatus } from "../types";

const STYLES: Record<TaskStatus, { label: string; cls: string }> = {
  queued_local: { label: "queued", cls: "bg-zinc-700 text-zinc-200" },
  queued_remote: { label: "waiting for slot", cls: "bg-amber-900 text-amber-200" },
  running: { label: "running", cls: "bg-blue-900 text-blue-200 animate-pulse" },
  verifying: { label: "verifying", cls: "bg-violet-900 text-violet-200" },
  succeeded: { label: "done ✓", cls: "bg-emerald-900 text-emerald-200" },
  done_unverified: { label: "done", cls: "bg-emerald-950 text-emerald-300" },
  failed: { label: "failed", cls: "bg-red-900 text-red-200" },
  cancelled: { label: "stopped", cls: "bg-zinc-800 text-zinc-400" },
};

export function StatusPill({ status }: { status: TaskStatus }) {
  const s = STYLES[status];
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${s.cls}`}>
      {s.label}
    </span>
  );
}
