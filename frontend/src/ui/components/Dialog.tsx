import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

const FOCUSABLE = "button, input, textarea, select, [href], [tabindex]:not([tabindex='-1'])";

export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    return () => trigger?.focus();
  }, []);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") return onClose();
    if (e.key !== "Tab") return;
    const items = Array.from(ref.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  return (
    <div className="overlay">
      <div ref={ref} className="dialog" role="dialog" aria-modal="true" aria-label={title} onKeyDown={onKeyDown}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}
