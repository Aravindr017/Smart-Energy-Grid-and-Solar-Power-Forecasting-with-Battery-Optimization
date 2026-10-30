import React from 'react';

export default function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center py-20" role="status" aria-live="polite">
      <div className="h-8 w-8 rounded-full border-2 border-emerald-200 border-t-emerald-600 animate-spin" />
      <span className="ml-3 text-sm text-slate-600">{label}</span>
    </div>
  );
}
