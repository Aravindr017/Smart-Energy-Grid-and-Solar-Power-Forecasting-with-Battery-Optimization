import React, { useId, useState } from 'react';
import { Info } from 'lucide-react';

export default function InfoTooltip({ label, children }) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        className="inline-flex text-slate-400 hover:text-slate-700"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute z-20 left-1/2 top-full mt-2 w-56 -translate-x-1/2 rounded-lg bg-navy-900 px-3 py-2 text-[11px] leading-relaxed text-white shadow-lg"
        >
          {children}
        </span>
      )}
    </span>
  );
}
