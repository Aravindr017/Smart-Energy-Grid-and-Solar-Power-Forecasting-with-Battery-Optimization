import React from 'react';

export default function FilterBar({ label, options, value, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {label && <span className="text-xs font-medium text-slate-500">{label}</span>}
      <div className="inline-flex rounded-xl bg-slate-100 p-1 text-xs">
        {options.map((option) => {
          const active = value === option.id;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onChange(option.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                active ? 'bg-white text-navy-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
