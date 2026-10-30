import React from 'react';

export default function PrimaryButton({ children, className = '', disabled, ...props }) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-emerald-700 text-white text-sm font-semibold shadow-sm hover:bg-emerald-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
