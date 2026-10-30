import React from 'react';

const tones = {
  success: 'bg-emerald-50 text-emerald-800',
  warning: 'bg-amber-50 text-amber-800',
  error: 'bg-red-50 text-red-800',
  info: 'bg-blue-50 text-blue-800',
  teal: 'bg-teal-50 text-teal-800',
  slate: 'bg-slate-100 text-slate-700',
  measured: 'bg-slate-100 text-slate-700',
  forecast: 'bg-amber-50 text-amber-800',
  estimated: 'bg-teal-50 text-teal-800',
};

export default function StatusBadge({ tone = 'slate', children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap ${tones[tone] || tones.slate} ${className}`}
    >
      {children}
    </span>
  );
}
