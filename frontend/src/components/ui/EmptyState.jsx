import React from 'react';

export default function EmptyState({ title = 'No data available', description }) {
  return (
    <div className="surface-card px-6 py-16 text-center">
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      {description && <p className="mt-1 text-sm text-slate-500 max-w-md mx-auto">{description}</p>}
    </div>
  );
}
