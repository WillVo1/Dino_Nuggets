import { ThinkingIndicator } from "./vendor/ThinkingIndicator";
import type { FeedEvent } from "../types";

interface Props {
  events: FeedEvent[];
  running: boolean;
}

/** Streaming agent feed: thinking paragraphs + action rows, dashboard-style. */
export function Feed({ events, running }: Props) {
  const items = events.filter((e) => ["thinking", "action", "answer"].includes(e.kind));

  return (
    <div className="space-y-2">
      {items.map((e) => {
        if (e.kind === "thinking") {
          return (
            <p key={e.seq} className="text-[13px] leading-relaxed text-zinc-400">
              {e.text}
            </p>
          );
        }
        if (e.kind === "action") {
          return (
            <div key={e.seq} className="flex items-center gap-2 py-0.5 text-[13px] text-zinc-200">
              <span className="text-emerald-400">✓</span>
              <span className="font-medium">{e.text}</span>
            </div>
          );
        }
        return (
          <div
            key={e.seq}
            className="mt-2 rounded-lg border border-emerald-900 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200"
          >
            Answer: {e.text}
          </div>
        );
      })}
      <ThinkingIndicator active={running} />
    </div>
  );
}
