import type { TaskStatus } from "../types";

const STYLES: Record<TaskStatus, { label: string; dot: string; text: string }> = {
  queued_local: { label: "Queued", dot: "bg-zinc-500", text: "text-zinc-400" },
  queued_remote: { label: "Waiting for slot", dot: "bg-amber-400", text: "text-amber-300/90" },
  running: { label: "Running", dot: "bg-blue-400 animate-pulse", text: "text-blue-300" },
  verifying: { label: "Verifying", dot: "bg-violet-400 animate-pulse", text: "text-violet-300" },
  succeeded: { label: "Verified", dot: "bg-emerald-400", text: "text-emerald-300" },
  done_unverified: { label: "Done", dot: "bg-emerald-500/70", text: "text-emerald-400/80" },
  failed: { label: "Failed", dot: "bg-red-400", text: "text-red-300" },
  cancelled: { label: "Stopped", dot: "bg-zinc-600", text: "text-zinc-500" },
};

export function StatusPill({ status }: { status: TaskStatus }) {
  const s = STYLES[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
