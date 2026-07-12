import { useEffect, useRef, useState } from "react";

/**
 * Reveal `text` progressively for a streaming feel. The hai API delivers each
 * reasoning block whole (no token deltas), so we simulate the stream client-side.
 * When `live` is false the text is shown in full immediately (historical events).
 */
export function useTypewriter(text: string, live: boolean, cps = 240): string {
  const [shown, setShown] = useState(live ? "" : text);
  const raf = useRef<number>();

  useEffect(() => {
    if (!live) {
      setShown(text);
      return;
    }
    let start: number | null = null;
    const step = (t: number) => {
      if (start === null) start = t;
      const n = Math.floor(((t - start) / 1000) * cps);
      setShown(text.slice(0, n));
      if (n < text.length) raf.current = requestAnimationFrame(step);
      else setShown(text);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [text, live, cps]);

  return shown;
}
