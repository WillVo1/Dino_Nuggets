import { useEffect, useRef } from "react";

import { api } from "../lib/api";
import type { FeedEvent, Task } from "../types";
import { screenshotSrc, TERMINAL } from "../types";
import { Feed } from "./Feed";
import { StatusPill } from "./StatusPill";

interface Props {
  task: Task;
  events: FeedEvent[];
}

export function SessionView({ task, events }: Props) {
  const running = !TERMINAL.includes(task.status);
  const feedRef = useRef<HTMLDivElement>(null);

  // auto-scroll the feed as events stream in
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center gap-3 border-b border-zinc-800 px-6 py-3">
        <StatusPill status={task.status} />
        <h1 className="truncate text-sm font-medium">{task.text}</h1>
        <span className="text-[11px] text-zinc-500">
          {task.worker} {task.steps > 0 && `· step ${task.steps} · $${task.cost_usd.toFixed(3)}`}
        </span>
        {running && (
          <button
            onClick={() => api.stopTask(task.id)}
            className="ml-auto rounded-lg border border-red-900 px-3 py-1 text-xs text-red-300 hover:bg-red-950"
          >
            Stop
          </button>
        )}
      </header>

      {task.status === "succeeded" && (
        <div className="border-b border-emerald-900 bg-emerald-950/50 px-6 py-2 text-sm text-emerald-200">
          ✓ Task completed — {task.verification}
        </div>
      )}
      {task.status === "failed" && task.verification && (
        <div className="border-b border-red-900 bg-red-950/50 px-6 py-2 text-sm text-red-200">
          ✗ {task.verification}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        {/* live view: newest frame */}
        <div className="flex w-3/5 items-start justify-center bg-black p-4">
          {task.last_screenshot_url ? (
            <img
              src={screenshotSrc(task.last_screenshot_url)}
              alt="live desktop"
              className="max-h-full rounded-lg border border-zinc-800"
            />
          ) : (
            <div className="mt-24 text-sm text-zinc-600">
              {task.status === "queued_remote"
                ? "waiting for a free session slot…"
                : "waiting for first frame…"}
            </div>
          )}
        </div>

        {/* streaming agent feed */}
        <div ref={feedRef} className="min-h-0 w-2/5 overflow-y-auto border-l border-zinc-800 p-4">
          <Feed events={events} running={running && task.status === "running"} />
        </div>
      </div>
    </div>
  );
}
