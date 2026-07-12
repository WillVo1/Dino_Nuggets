import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";

interface ThinkingIndicatorProps {
  /** Whether the thinking state is currently active. */
  active: boolean;
  /** When hosted inside an assistant turn's content flow (e.g. the ToolSteps
   *  activity slot), match the active tool-step row's `4px 0` padding and drop
   *  the standalone top margin so "Thinking" lines up with the active tool row. */
  inline?: boolean;
}

const wrapperStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "5px",
  padding: "2px 0",
  fontSize: "13px",
  fontWeight: 500,
  color: "var(--og2-secondary-text, #a1a1aa)",
  marginTop: "2px",
};

const inlineWrapperStyle: CSSProperties = {
  padding: "4px 0",
  marginTop: 0,
};

export const shimmerStyle: CSSProperties = {
  display: "inline-block",
  color: "var(--og2-shimmer-color, rgba(0, 0, 0, 0.27))",
  background: [
    "linear-gradient(90deg,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 0%,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 50%,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 54%,",
    "var(--og2-shimmer-mid1, rgba(0,0,0,0.3)) 57%,",
    "var(--og2-shimmer-mid2, rgba(0,0,0,0.34)) 61%,",
    "var(--og2-shimmer-highlight, rgba(0,0,0,0.42)) 66%,",
    "var(--og2-shimmer-highlight, rgba(0,0,0,0.42)) 74%,",
    "var(--og2-shimmer-mid2, rgba(0,0,0,0.34)) 79%,",
    "var(--og2-shimmer-mid1, rgba(0,0,0,0.3)) 83%,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 88%,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 92%,",
    "var(--og2-shimmer-base, rgba(0,0,0,0.22)) 100%)",
  ].join(" "),
  backgroundSize: "200% 100%",
  backgroundRepeat: "repeat-x",
  backgroundClip: "text",
  WebkitBackgroundClip: "text",
  WebkitTextFillColor: "transparent",
  willChange: "background-position, opacity",
  animation: "og2-shimmer 1s linear infinite",
  lineHeight: "inherit",
};

export const SHIMMER_KEYFRAMES = `
  @keyframes og2-shimmer {
    0%   { background-position: 0% 0; opacity: 0.98; }
    15%  { opacity: 1; }
    86%  { background-position: -200% 0; opacity: 1; }
    100% { background-position: -202% 0; opacity: 0.99; }
  }
`;

/**
 * Thinking indicator — a shimmer "Thinking" text.
 *
 * Detached placement (fresh turn) debounces by 900ms to avoid flashing for
 * fast responses. Inline placement shows immediately: it only ever renders
 * mid-turn, after the turn has already produced a step or text, so work is
 * provably in flight and there is no fast-response to guard against. Debouncing
 * there would just leave a dead gap between a finished step and the shimmer,
 * making the completed-steps row above appear to bounce.
 *
 * All styles are fully inline with CSS-variable hooks so the gradient
 * adapts to dark/light mode via --og2-shimmer-* variables set in
 * appearance.ts.
 */
export function ThinkingIndicator({ active, inline }: ThinkingIndicatorProps) {
  const [show, setShow] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (active) {
      if (inline) {
        setShow(true);
      } else {
        timerRef.current = setTimeout(() => setShow(true), 900);
      }
    } else {
      setShow(false);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [active, inline]);

  if (!show) return null;
  return (
    <>
      <style>{SHIMMER_KEYFRAMES}</style>
      <div style={inline ? { ...wrapperStyle, ...inlineWrapperStyle } : wrapperStyle}>
        <span style={shimmerStyle}>Thinking</span>
      </div>
    </>
  );
}
