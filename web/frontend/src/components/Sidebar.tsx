import { api } from "../lib/api";
import type { Task, Worker } from "../types";
import { TERMINAL } from "../types";
import { StatusPill } from "./StatusPill";

interface Props {
  tasks: Task[];
  workers: Worker[];
  selected: string | null;
  onSelect: (id: string | null) => void;
  onNewTask: () => void;
  onClearCompleted: () => void;
}

export function Sidebar({
  tasks, workers, selected, onSelect, onNewTask, onClearCompleted,
}: Props) {
  const active = tasks.filter((t) => !TERMINAL.includes(t.status));
  const completed = tasks.filter((t) => TERMINAL.includes(t.status));

  async function clearCompleted() {
    await api.clearCompleted();
    onClearCompleted();
  }

  const Item = ({ t }: { t: Task }) => (
    <button
      onClick={() => onSelect(t.id)}
      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
        selected === t.id ? "bg-zinc-800" : "hover:bg-zinc-900"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate">{t.text}</span>
        <StatusPill status={t.status} />
      </div>
      {t.worker && <div className="mt-0.5 text-[11px] text-zinc-500">{t.worker}</div>}
    </button>
  );

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-zinc-850 bg-zinc-950 p-3">
      <button
        onClick={() => onSelect(null)}
        className="mb-3 text-left text-lg font-semibold tracking-tight"
      >
        Tryton Fleet
      </button>
      <button
        onClick={onNewTask}
        className="mb-4 rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 hover:bg-white"
      >
        + New task
      </button>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        {active.length > 0 && (
          <section>
            <h3 className="mb-1 px-1 text-[11px] font-semibold uppercase text-zinc-500">
              Active
            </h3>
            {active.map((t) => <Item key={t.id} t={t} />)}
          </section>
        )}
        {completed.length > 0 && (
          <section>
            <div className="mb-1 flex items-center justify-between px-1">
              <h3 className="text-[11px] font-semibold uppercase text-zinc-500">
                Completed
              </h3>
              <button
                onClick={clearCompleted}
                className="text-[11px] text-zinc-600 hover:text-zinc-300"
              >
                Clear
              </button>
            </div>
            {completed.map((t) => <Item key={t.id} t={t} />)}
          </section>
        )}
      </div>

      <footer className="mt-3 shrink-0 border-t border-zinc-850 pt-2">
        <h3 className="mb-1 text-[11px] font-semibold uppercase text-zinc-500">Workers</h3>
        {workers.map((w) => (
          <div key={w.name} className="flex items-center gap-2 py-0.5 text-xs text-zinc-400">
            <span
              className={`h-2 w-2 rounded-full ${
                w.status === "idle" ? "bg-emerald-500"
                : w.status === "busy" ? "bg-blue-500"
                : "bg-zinc-600"
              }`}
            />
            {w.name}
            <span className="ml-auto text-zinc-600">{w.status}</span>
          </div>
        ))}
      </footer>
    </aside>
  );
}
