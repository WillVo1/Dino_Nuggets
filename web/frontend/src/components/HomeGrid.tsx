import type { Task } from "../types";
import { screenshotSrc, TERMINAL } from "../types";
import { StatusPill } from "./StatusPill";

interface Props {
  tasks: Task[];
  onSelect: (id: string) => void;
}

/** Home: one live tile per active task + the decorative "my computer" tile. */
export function HomeGrid({ tasks, onSelect }: Props) {
  const active = tasks.filter((t) => !TERMINAL.includes(t.status));

  return (
    <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-2 xl:grid-cols-3">
      {active.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className="group overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900 text-left transition-colors hover:border-zinc-600"
        >
          <div className="relative aspect-[8/5] bg-black">
            {t.last_screenshot_url ? (
              <img
                src={screenshotSrc(t.last_screenshot_url)}
                alt="agent desktop"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-zinc-600">
                waiting for first frame…
              </div>
            )}
            <div className="absolute left-2 top-2">
              <StatusPill status={t.status} />
            </div>
          </div>
          <div className="flex items-center justify-between px-3 py-2">
            <span className="truncate text-sm">{t.text}</span>
            <span className="ml-2 shrink-0 text-[11px] text-zinc-500">
              {t.steps > 0 && `step ${t.steps} · $${t.cost_usd.toFixed(3)}`}
            </span>
          </div>
        </button>
      ))}

      {/* decorative "my computer" tile — represents the Mac, deliberately static */}
      <div className="flex aspect-[8/5] flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 text-zinc-600">
        <div className="text-3xl">🖥️</div>
        <div className="mt-2 text-xs">my computer — never driven</div>
      </div>

      {active.length === 0 && (
        <div className="col-span-full py-16 text-center text-sm text-zinc-500">
          No active tasks. Hit <span className="text-zinc-300">+ New task</span> to dispatch one.
        </div>
      )}
    </div>
  );
}
