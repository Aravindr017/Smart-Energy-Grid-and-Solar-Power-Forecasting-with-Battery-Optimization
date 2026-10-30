import React from 'react';
import StatusBadge from './StatusBadge';

export default function MetricCard({
  label,
  value,
  unit,
  subtitle,
  icon: Icon,
  tone = 'emerald',
  badge,
}) {
  const tones = {
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    blue: 'bg-blue-50 text-blue-700',
    orange: 'bg-orange-50 text-orange-700',
    teal: 'bg-teal-50 text-teal-700',
    navy: 'bg-navy-50 text-navy-800',
    slate: 'bg-slate-100 text-slate-600',
    red: 'bg-red-50 text-red-700',
  };

  return (
    <div className="surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="muted-label">{label}</span>
        {Icon && (
          <span className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${tones[tone] || tones.emerald}`}>
            <Icon className="w-4 h-4" aria-hidden="true" />
          </span>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5 min-w-0">
        <span className="kpi-value truncate">{value}</span>
        {unit && <span className="text-sm font-medium text-slate-500">{unit}</span>}
      </div>
      {(subtitle || badge) && (
        <div className="mt-2 flex items-center justify-between gap-2">
          {subtitle && <p className="text-xs text-slate-500 leading-snug">{subtitle}</p>}
          {badge && <StatusBadge tone={badge.tone}>{badge.label}</StatusBadge>}
        </div>
      )}
    </div>
  );
}
