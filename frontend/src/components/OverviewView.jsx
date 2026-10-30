import React from 'react';
import { Sun, Activity, DollarSign, Leaf, CloudSun } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import PageHeader from './ui/PageHeader';
import MetricCard from './ui/MetricCard';
import ChartCard from './ui/ChartCard';
import FilterBar from './ui/FilterBar';
import LoadingState from './ui/LoadingState';
import EmptyState from './ui/EmptyState';
import ErrorState from './ui/ErrorState';
import LegendItem from './ui/LegendItem';
import StatusBadge from './ui/StatusBadge';
import { COLORS, tooltipStyle, axisProps, formatNumber, formatMoney } from './ui/chartTheme';

export default function OverviewView({
  data,
  plantInfo,
  granularity,
  setGranularity,
  loading,
  error,
  onRetry,
  forecastData,
  optData,
}) {
  if (loading && !data) {
    return <LoadingState label="Loading plant generation…" />;
  }

  if (error && !data) {
    return <ErrorState title="Overview data is unavailable" message={error} onRetry={onRetry} />;
  }

  if (!data?.kpis) {
    return (
      <EmptyState
        title="Overview data is unavailable"
        description="The plant telemetry service did not return results for this selection."
      />
    );
  }

  const { kpis, timeseries } = data;
  const optKpis = optData?.kpis || {};
  const schedule = optData?.schedule || [];
  const predictions = forecastData?.predictions || [];
  const capacityFactorPct = plantInfo?.rated_capacity_mw > 0
    ? (kpis.avg_ac_kw / (plantInfo.rated_capacity_mw * 1000)) * 100
    : null;

  const latestActual = timeseries?.length ? timeseries[timeseries.length - 1] : null;
  const nextAction = schedule.find((row) => row.charge_mw > 0.01 || row.discharge_mw > 0.01);
  const actionLabel = nextAction
    ? nextAction.charge_mw > 0.01
      ? `Charge at ${nextAction.hour}`
      : `Discharge at ${nextAction.hour}`
    : 'No charge or discharge scheduled';

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="What you are looking at"
        title={plantInfo?.name || 'Solar plant overview'}
        description="Measured generation, plant capacity factor, average power, and estimated savings from the current optimization run."
        actions={
          <FilterBar
            label="Time resolution"
            value={granularity}
            onChange={setGranularity}
            options={[
              { id: 'hourly', label: 'Hourly' },
              { id: '15min_plant', label: '15-min plant' },
              { id: '15min', label: '15-min inverter' },
            ]}
          />
        }
      />

      <p className="text-xs text-slate-500">
        {plantInfo?.location_name} · {plantInfo?.latitude}° N, {plantInfo?.longitude}° E · {plantInfo?.elevation_m} m
        elevation · {plantInfo?.inverters_count} inverters
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Solar generation"
          value={formatNumber(kpis.total_energy_mwh, 1)}
          unit="MWh"
          subtitle={`${formatNumber(kpis.peak_ac_kw, 0)} kW peak measured output`}
          icon={Sun}
          tone="amber"
          badge={{ label: 'Measured', tone: 'measured' }}
        />
        <MetricCard
          label="Capacity factor"
          value={capacityFactorPct != null ? formatNumber(capacityFactorPct, 1) : '—'}
          unit="%"
          subtitle="Average measured output vs. rated capacity"
          icon={Activity}
          tone="blue"
          badge={{ label: 'Measured', tone: 'measured' }}
        />
        <MetricCard
          label="Mean active power"
          value={formatNumber(kpis.avg_ac_kw, 1)}
          unit="kW"
          subtitle="Time-averaged measured output"
          icon={Activity}
          tone="emerald"
          badge={{ label: 'Measured', tone: 'measured' }}
        />
        <MetricCard
          label="Estimated cost savings"
          value={optKpis.net_arbitrage_savings != null ? `$${formatMoney(optKpis.net_arbitrage_savings)}` : '—'}
          subtitle="Net 24-hour arbitrage after degradation"
          icon={DollarSign}
          tone="emerald"
          badge={{ label: 'Estimated', tone: 'estimated' }}
        />
      </div>

      <ChartCard
        title="Solar generation trend"
        description="Measured AC power against solar irradiance for the selected resolution."
        legend={
          <div className="flex flex-wrap gap-4">
            <LegendItem color={COLORS.solar} label="AC power (kW)" />
            <LegendItem color={COLORS.ghi} label="GHI (W/m²)" dashed />
          </div>
        }
      >
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeseries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="time" {...axisProps} />
              <YAxis
                yAxisId="left"
                {...axisProps}
                axisLine={false}
                tickFormatter={(val) => `${(val / 1000).toFixed(1)}k`}
              />
              <YAxis yAxisId="right" orientation="right" {...axisProps} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="ac_power_kw"
                name="AC Power (kW)"
                fill={COLORS.solarFill}
                stroke={COLORS.solar}
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="ghi"
                name="GHI (W/m²)"
                stroke={COLORS.ghi}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <ChartCard
          className="xl:col-span-2"
          title="Forecast versus measured generation"
          description={
            predictions.length
              ? 'Where both series exist, LightGBM forecast is shown against measured AC power.'
              : 'Forecast observations are not available for this view yet.'
          }
        >
          <div className="h-64 w-full">
            {predictions.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={predictions.slice(-48)} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="time" {...axisProps} />
                  <YAxis {...axisProps} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line type="monotone" dataKey="actual" name="Measured (kW)" stroke={COLORS.actual} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="lightgbm" name="Forecast (kW)" stroke={COLORS.lightgbm} strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="No overlapping forecast points" description="Open Solar Forecast for the full comparison." />
            )}
          </div>
        </ChartCard>

        <section className="surface-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-900">Battery and weather</h3>
          <div>
            <p className="muted-label">Next scheduled operation</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{actionLabel}</p>
            <p className="text-xs text-slate-500 mt-1">From the latest 24-hour optimization schedule.</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 text-sm">
            <div className="flex items-center gap-2 text-slate-700">
              <CloudSun className="w-4 h-4 text-solar-600" />
              Latest measured conditions
            </div>
            <p className="mt-2 text-slate-600 text-xs leading-relaxed">
              {latestActual
                ? `${latestActual.ambient_temp_c}°C ambient, ${latestActual.module_temp_c}°C module, GHI ${latestActual.ghi} W/m²`
                : 'Weather telemetry is not available in the current slice.'}
            </p>
          </div>
        </section>
      </div>

      <section className="surface-card p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold text-slate-900">Carbon and system status</h3>
          <StatusBadge tone="info">Estimates only</StatusBadge>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="muted-label">Observation window</p>
            <p className="mt-1 font-semibold text-slate-900">
              {kpis.date_start} to {kpis.date_end}
            </p>
            <p className="text-xs text-slate-500 mt-1">{formatNumber(kpis.total_records, 0)} records</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="muted-label">Mean active power</p>
            <p className="mt-1 font-semibold text-slate-900">{formatNumber(kpis.avg_ac_kw, 1)} kW</p>
            <p className="text-xs text-slate-500 mt-1">Time-averaged measured output</p>
          </div>
          <div className="rounded-xl bg-emerald-50 p-4">
            <div className="flex items-center gap-2 text-emerald-800">
              <Leaf className="w-4 h-4" />
              <p className="muted-label !text-emerald-700">Carbon</p>
            </div>
            <p className="mt-1 text-sm text-emerald-900">
              Open Environmental Benefits for estimated CO₂ emissions avoided. Figures are estimates, not certified offsets.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
