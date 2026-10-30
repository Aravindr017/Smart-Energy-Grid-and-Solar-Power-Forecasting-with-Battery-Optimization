import React from 'react';

export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <p className="muted-label mb-2">{eyebrow}</p>}
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">{title}</h2>
        {description && (
          <p className="mt-1.5 text-sm text-slate-500 max-w-3xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
