export const COLORS = {
  solar: '#d97706',
  solarFill: '#fef3c7',
  charge: '#059669',
  discharge: '#2563eb',
  idle: '#94a3b8',
  gridImport: '#ea580c',
  gridExport: '#0d9488',
  demand: '#475569',
  netLoad: '#0f766e',
  ghi: '#b45309',
  moduleTemp: '#dc2626',
  ambientTemp: '#2563eb',
  actual: 'var(--chart-actual)',
  lightgbm: '#059669',
  xgboost: '#f97316',
  prophet: '#7c3aed',
  ridge: '#2563eb',
  persistence: '#64748b',
  bounds: '#fde68a',
  unmanaged: '#ea580c',
  managed: '#059669',
  navy: '#0b1f33',
};

export const tooltipStyle = {
  backgroundColor: 'var(--dashboard-surface)',
  border: '1px solid var(--dashboard-border)',
  borderRadius: '0.75rem',
  fontSize: '0.75rem',
  boxShadow: '0 10px 20px -8px rgba(15, 23, 42, 0.18)',
  color: 'var(--dashboard-text)',
};

export const axisProps = {
  stroke: 'var(--dashboard-muted)',
  fontSize: 11,
  tickLine: false,
};

export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
