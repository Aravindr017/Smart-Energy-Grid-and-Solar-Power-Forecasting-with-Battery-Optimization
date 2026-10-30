import React from 'react';

export default function SectionHeader({ title, description, actions }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {description && <p className="text-xs text-slate-500 mt-0.5 max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3 shrink-0">{actions}</div>}
    </div>
  );
}
