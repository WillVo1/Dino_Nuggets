/** Mirrors backend app/models.py */

export type TaskStatus =
  | "queued_local"
  | "queued_remote"
  | "running"
  | "verifying"
  | "succeeded"
  | "done_unverified"
  | "failed"
  | "cancelled";

export const TERMINAL: TaskStatus[] = ["succeeded", "done_unverified", "failed", "cancelled"];

export interface Task {
  id: string;
  text: string;
  prompt: string;
  preset: string | null;
  status: TaskStatus;
  worker: string | null;
  hai_session_id: string | null;
  answer: string | null;
  outcome: string | null;
  verification: string | null;
  steps: number;
  cost_usd: number;
  last_screenshot_url: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface FeedEvent {
  task_id: string;
  seq: number;
  kind: "thinking" | "action" | "screenshot" | "answer" | "status" | "metrics";
  text: string | null;
  tool: string | null;
  args: Record<string, unknown> | null;
  image_url: string | null;
  step: number | null;
  cost_usd: number | null;
  ts: string;
}

export interface Worker {
  name: string;
  ip: string;
  session_id: string | null;
  status: "idle" | "busy" | "offline";
  current_task_id: string | null;
}

export interface Preset {
  key: string;
  label: string;
}

export const screenshotSrc = (url: string) =>
  `/api/screenshot?url=${encodeURIComponent(url)}`;
