"use client";

import { useId, useState } from "react";

export function HelpTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return <span className="help-tooltip" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" className="help-tooltip__trigger" aria-label={`Help: ${label}`} aria-expanded={open} aria-controls={id} aria-describedby={open ? id : undefined}
      onClick={() => setOpen(true)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={(event) => { if (event.key === "Escape") { setOpen(false); event.stopPropagation(); } }}>?</button>
    <span id={id} role="tooltip" className="help-tooltip__content" hidden={!open}>{children}</span>
  </span>;
}
