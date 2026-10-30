import React from 'react';

export default function LegendItem({ color, label, dashed = false }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-600">
      <span
        className={`w-3 ${dashed ? 'h-0.5 border-t-2 border-dashed' : 'h-2 rounded-sm'}`}
        style={dashed ? { borderColor: color } : { backgroundColor: color }}
      />
      <span>{label}</span>
    </div>
  );
}
