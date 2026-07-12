import type { CSSProperties } from "react";
import { useState } from "react";

import { SHIMMER_KEYFRAMES, ThinkingIndicator } from "./ThinkingIndicator.js";

export interface ToolCallInfo {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: "calling" | "done" | "error";
  providerMetadata?: Record<string, unknown>;
}

export interface ToolStepsProps {
  toolCalls: ToolCallInfo[];
  /** True while an `ask_user` card is awaiting input — freezes the trailing
   *  step at a green tick (no spinner, no shimmer) since the turn is parked
   *  on the human, not in flight. */
  awaitingUserInput?: boolean;
  hasContent?: boolean;
  isStreaming?: boolean;
  /** Parent-computed: render the "Thinking" shimmer in the current-activity slot
   *  when no tool is in flight. Lets the live tool-steps block host the shimmer
   *  in the exact slot the active row uses (zero vertical residual). */
  thinking?: boolean;
  spinnerClassName?: string;
  formatToolCall: (tc: ToolCallInfo) => string;
}

/* ── Inline style constants ── */

const toolStepsStyle: CSSProperties = {
  padding: "2px 0 4px",
};

const toolCurrentStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "5px",
};

const stepDoneStyle: CSSProperties = {
  display: "inline-block",
  fontSize: "13px",
  fontWeight: 500,
  color: "#a1a1aa",
  padding: "2px 0",
};

const stepCheckStyle: CSSProperties = {
  display: "inline-block",
  verticalAlign: "middle",
  marginLeft: "4px",
  color: "#22c55e",
  flexShrink: 0,
  animation: "og2-ts-check-in 0.3s ease-out",
};

const stepCrossStyle: CSSProperties = {
  ...stepCheckStyle,
  color: "#ef4444",
};

const expandedStepStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "5px",
  padding: "2px 0 2px 4px",
  fontSize: "12px",
};

const expandedStepDoneStyle: CSSProperties = {
  ...stepDoneStyle,
  fontSize: "12px",
  color: "#c4c4cc",
};

const summaryBtnStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "4px",
  background: "none",
  border: "none",
  padding: "2px 0",
  cursor: "pointer",
  fontFamily: "inherit",
};

const chevronStyle: CSSProperties = {
  color: "#a1a1aa",
  flexShrink: 0,
  transition: "transform 0.15s ease",
};

const activeTextStyle: CSSProperties = {
  display: "inline-block",
  fontSize: "13px",
  fontWeight: 500,
  color: "#a1a1aa",
  padding: "4px 0",
};

/* ── Keyframes that must live in a <style> tag ── */

const TOOLSTEPS_KEYFRAMES = `
  @keyframes og2-ts-check-in {
    0%   { opacity: 0; transform: scale(0.5); }
    100% { opacity: 1; transform: scale(1); }
  }
`;

export function ToolSteps({
  toolCalls,
  awaitingUserInput,
  hasContent,
  isStreaming,
  thinking,
  spinnerClassName,
  formatToolCall: fmtToolCall,
}: ToolStepsProps) {
  const [expanded, setExpanded] = useState(false);

  const latest = toolCalls[toolCalls.length - 1];
  const count = toolCalls.length;

  // Active only while a tool is genuinely in flight. A trailing step freezes
  // at a green tick while parked on the user. (A `done` screen-capture that's
  // awaiting the model is NOT held active here — the global ThinkingIndicator
  // covers that window, so holding a spinner too would double up.)
  const isActive = !awaitingUserInput && latest.status === "calling";

  const allDone = !isActive && !awaitingUserInput && !thinking && (hasContent || !isStreaming);

  // A finished step is either "done" or "error" — a failed step still appears
  // in the completed list (rendered with a cross), it doesn't vanish.
  const doneSteps = toolCalls.filter(
    (tc) => (tc.status === "done" || tc.status === "error") && (!isActive || tc.id !== latest.id),
  );

  const chevronSvg = (rotated: boolean) => (
    <svg
      style={{
        ...chevronStyle,
        ...(rotated ? { transform: "rotate(90deg)" } : {}),
      }}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );

  const checkIcon = (
    <svg
      style={stepCheckStyle}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={3}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );

  const crossIcon = (
    <svg
      style={stepCrossStyle}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={3}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );

  // Per-step terminal marker: green tick for a completed step, red cross for
  // a failed one (e.g. an OpenAPI server tool whose API returned a 4xx/5xx).
  const statusIcon = (status: ToolCallInfo["status"]) =>
    status === "error" ? crossIcon : checkIcon;

  if (allDone) {
    return (
      <div style={toolStepsStyle}>
        <style>{TOOLSTEPS_KEYFRAMES}</style>
        <button style={summaryBtnStyle} onClick={() => setExpanded(!expanded)} type="button">
          <span style={stepDoneStyle}>
            {count} step{count !== 1 ? "s" : ""}
            {checkIcon}
          </span>
          {chevronSvg(expanded)}
        </button>
        {expanded &&
          toolCalls.map((tc) => (
            <div key={tc.id} style={expandedStepStyle}>
              <span style={expandedStepDoneStyle}>
                {fmtToolCall(tc)}
                {statusIcon(tc.status)}
              </span>
            </div>
          ))}
      </div>
    );
  }

  return (
    <div style={toolStepsStyle}>
      <style>
        {SHIMMER_KEYFRAMES}
        {TOOLSTEPS_KEYFRAMES}
      </style>
      {doneSteps.length > 0 && (
        <>
          <button style={summaryBtnStyle} onClick={() => setExpanded(!expanded)} type="button">
            <span style={stepDoneStyle}>
              {doneSteps.length} completed{checkIcon}
            </span>
            {chevronSvg(expanded)}
          </button>
          {expanded &&
            doneSteps.map((tc) => (
              <div key={tc.id} style={expandedStepStyle}>
                <span style={expandedStepDoneStyle}>
                  {fmtToolCall(tc)}
                  {statusIcon(tc.status)}
                </span>
              </div>
            ))}
        </>
      )}
      {isActive && (
        <div style={toolCurrentStyle}>
          {spinnerClassName && <span className={spinnerClassName} />}
          <span style={activeTextStyle}>{fmtToolCall(latest)}</span>
        </div>
      )}
      {!isActive && thinking && <ThinkingIndicator active inline />}
    </div>
  );
}
