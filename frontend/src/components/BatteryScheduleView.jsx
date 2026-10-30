import React from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import PageHeader from './ui/PageHeader';
import MetricCard from './ui/MetricCard';
import ChartCard from './ui/ChartCard';
import LoadingState from './ui/LoadingState';
import ErrorState from './ui/ErrorState';
import PrimaryButton from './ui/PrimaryButton';
import LegendItem from './ui/LegendItem';
import StatusBadge from './ui/StatusBadge';
import { COLORS, axisProps, formatNumber, formatINR } from './ui/chartTheme';

const formatScheduleTime = (time) => {
  const [hourText, minute] = time.split(':');
  const hour = Number(hourText);
  return `${hour % 12 || 12}:${minute} ${hour < 12 ? 'AM' : 'PM'}`;
};

export default function BatteryScheduleView({
  optData,
  params,
  setParams,
  onRunOptimization,
  loading,
}) {
  const handleSliderChange = (key, value) => {
    setParams((prev) => ({ ...prev, [key]: Number(value) }));
  };

  const schedule = optData?.schedule || [];
  const kpis = optData?.kpis || {};
  const socGauge = optData?.soc_gauge || {};
  const failed = !loading && optData && !schedule.length;

  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const currentSoc = socGauge.final_soc_pct ?? params.initial_soc_pct ?? 0;
  const strokeDashoffset = circumference - (currentSoc / 100) * circumference;

  const nextAction = schedule.find((row) => row.charge_mw > 0.01 || row.discharge_mw > 0.01);

  if (loading && !optData) {
    return <LoadingState label="Solving battery schedule…" />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Battery schedule"
        description={Number.isFinite(params.off_peak_rate) && Number.isFinite(params.normal_rate) && Number.isFinite(params.peak_rate)
          ? `Estimated battery dispatch uses simulated INR tariffs: ₹${params.off_peak_rate.toFixed(2)}/kWh off-peak (22:00–06:00), ₹${params.normal_rate.toFixed(2)}/kWh normal (10:00–18:00), and ₹${params.peak_rate.toFixed(2)}/kWh peak (06:00–10:00 and 18:00–22:00). Green is charging, blue is discharging, gray is idle.`
          : 'Estimated battery dispatch uses simulated INR tariff assumptions. Green is charging, blue is discharging, gray is idle.'}
        actions={
          <PrimaryButton onClick={onRunOptimization} disabled={loading}>
            {loading ? 'Solving…' : 'Run optimization'}
          </PrimaryButton>
        }
      />

      {failed && (
        <ErrorState
          title="Optimization did not return a schedule"
          message="The solver may be infeasible with the current constraints. Adjust capacity, power, or initial state of charge and run again."
          onRetry={onRunOptimization}
        />
      )}

      <section className="surface-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold text-slate-900">Battery settings</h3>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Solar generation data:</span>
            <button
              type="button"
              onClick={() => {
                setParams((prev) => ({ ...prev, use_forecast: prev.use_forecast === false ? true : false }));
              }}
              className={`px-2.5 py-1 rounded-lg font-medium border transition-colors ${
                params.use_forecast !== false
                  ? 'bg-emerald-600 text-white border-emerald-600'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}
            >
              {params.use_forecast !== false ? 'Next 24-hour forecast' : 'Past 24-hour data'}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 text-sm">
          {[
            {
              key: 'battery_capacity_mwh',
              label: 'Battery Capacity',
              value: `${params.battery_capacity_mwh} MWh`,
              min: 1,
              max: 30,
              step: 1,
              hint: 'How much energy the battery can store',
            },
            {
              key: 'max_inverter_power_mw',
              label: 'Maximum Charge / Discharge Power',
              value: `${params.max_inverter_power_mw} MW`,
              min: 0.5,
              max: 15,
              step: 0.5,
              hint: 'Fastest the battery can charge or discharge',
            },
            {
              key: 'round_trip_efficiency_pct',
              label: 'Battery Efficiency',
              value: `${params.round_trip_efficiency_pct}%`,
              min: 75,
              max: 98,
              step: 0.5,
              hint: 'Energy available after charging and discharging',
            },
            {
              key: 'initial_soc_pct',
              label: 'Starting Battery Level',
              value: `${params.initial_soc_pct}%`,
              min: 10,
              max: 80,
              step: 5,
              hint: 'Battery level to keep at the end of the schedule',
            },
          ].map((item) => (
            <div key={item.key} className="space-y-1.5">
              <div className="flex justify-between font-medium">
                <span className="text-slate-600">{item.label}</span>
                <span className="text-slate-900">{item.value}</span>
              </div>
              <input
                type="range"
                min={item.min}
                max={item.max}
                step={item.step}
                value={params[item.key]}
                onChange={(e) => handleSliderChange(item.key, e.target.value)}
                className="range-control"
                aria-label={item.label}
              />
              <p className="text-[11px] text-slate-400">{item.hint}</p>
            </div>
          ))}
        </div>

        <div className="mt-5 pt-5 border-t border-slate-100">
          <p className="text-xs font-semibold text-slate-700">Electricity Rates</p>
          <p className="text-[11px] text-slate-400 mb-3">
            Simulated prices for buying or exporting electricity, in INR/kWh. Financial results are estimates, not actual bills or guaranteed savings.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {[
              { key: 'off_peak_rate', label: 'Low-Cost Electricity' },
              { key: 'normal_rate', label: 'Normal-Cost Electricity' },
              { key: 'peak_rate', label: 'Peak Electricity (6–10 AM, 6–10 PM)' },
              { key: 'export_feedin_rate', label: 'Money Earned from Extra Solar Power' },
            ].map((item) => (
              <label key={item.key} className="block">
                <span className="block text-xs text-slate-500 mb-1">{item.label}</span>
                <input
                  type="number"
                  step="0.1"
                  value={params[item.key]}
                  onChange={(e) => handleSliderChange(item.key, e.target.value)}
                  className="input-control font-mono"
                />
              </label>
            ))}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Battery Level"
          value={socGauge.final_soc_pct != null ? formatNumber(socGauge.final_soc_pct, 1) : '—'}
          unit="%"
          subtitle="End of the 24-hour schedule"
          tone="blue"
        />
        <MetricCard
          label="Capacity"
          value={params.battery_capacity_mwh}
          unit="MWh"
          subtitle={`Power limit ${params.max_inverter_power_mw} MW`}
          tone="emerald"
        />
        <MetricCard
          label="Throughput"
          value={kpis.battery_total_throughput_kwh != null ? formatNumber(kpis.battery_total_throughput_kwh / 1000, 2) : '—'}
          unit="MWh"
          subtitle={`${formatNumber(kpis.equivalent_full_cycles, 2)} equivalent cycles`}
          tone="navy"
        />
        <MetricCard
          label="Estimated savings"
          value={formatINR(kpis.net_arbitrage_savings)}
          subtitle={`Estimated battery wear ${formatINR(kpis.degradation_wear_cost)}`}
          tone="emerald"
          badge={{ label: 'Estimated', tone: 'estimated' }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="surface-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">Battery Level</h3>
            <StatusBadge tone="info" className="whitespace-normal text-center">
              Recommended Battery Range: 10%–90%
            </StatusBadge>
          </div>
          <div className="flex items-center justify-center my-4">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" aria-hidden="true">
                <circle cx="88" cy="88" r={radius} stroke="#e2e8f0" strokeWidth="12" fill="transparent" />
                <circle
                  cx="88"
                  cy="88"
                  r={radius}
                  stroke={COLORS.charge}
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="absolute text-center">
                <p className="text-3xl font-semibold text-slate-900">{Number(currentSoc).toFixed(1)}%</p>
                <p className="text-[11px] text-slate-500">Final Battery Level</p>
              </div>
            </div>
          </div>
          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex justify-between">
              <span>Final Battery Limit</span>
              <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
                {socGauge.terminal_condition_met !== false ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Satisfied
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Check result
                  </>
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Next Battery Action</span>
              <span className="font-medium text-slate-800">
                {nextAction
                  ? `${nextAction.charge_mw > 0.01 ? 'Charge' : 'Discharge'} at ${formatScheduleTime(nextAction.hour)}`
                  : 'Idle'}
              </span>
            </div>
          </div>
        </section>

        <section className="lg:col-span-2 surface-card p-5">
          <h3 className="text-sm font-semibold text-slate-900">Battery Safety Limits</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            Battery limits for the current schedule.
          </p>
          <div className="relative w-full h-8 bg-slate-100 rounded-lg overflow-hidden flex text-[10px] font-medium">
            <div className="w-[10%] bg-red-100 text-red-700 flex items-center justify-center">Too Low</div>
            <div className="w-[80%] bg-emerald-50 text-slate-600 flex items-center justify-center relative">
              Safe Battery Level (10%–90%)
              {socGauge.min_soc_pct != null && socGauge.max_soc_pct != null && (
                <div
                  className="absolute h-full bg-emerald-400/50"
                  style={{
                    left: `${Math.max(0, (socGauge.min_soc_pct - 10) / 0.8)}%`,
                    width: `${Math.min(100, (socGauge.max_soc_pct - socGauge.min_soc_pct) / 0.8)}%`,
                  }}
                />
              )}
            </div>
            <div className="w-[10%] bg-red-100 text-red-700 flex items-center justify-center">Too High</div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4 text-xs">
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-slate-500">Minimum Battery Level</p>
              <p className="text-lg font-semibold">{socGauge.min_soc_pct != null ? `${socGauge.min_soc_pct.toFixed(1)}%` : '—'}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-slate-500">Maximum Battery Level</p>
              <p className="text-lg font-semibold">{socGauge.max_soc_pct != null ? `${socGauge.max_soc_pct.toFixed(1)}%` : '—'}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-slate-500">Reduction in Peak Grid Usage</p>
              <p className="text-lg font-semibold">{kpis.peak_shaving_percentage != null ? `${kpis.peak_shaving_percentage.toFixed(1)}%` : '—'}</p>
            </div>
          </div>
        </section>
      </div>

      <ChartCard
        title="Battery Charging & Usage — Next 24 Hours"
        description="Green bars show when and how fast the battery charges. Blue bars show power supplied from the battery. The purple line shows the battery level; hover over an hour to see how much energy remains."
        legend={
          <div className="flex flex-wrap gap-4">
            <LegendItem color={COLORS.charge} label="Charging Power (MW)" />
            <LegendItem color={COLORS.discharge} label="Power Supplied (MW)" />
            <LegendItem color="#7c3aed" label="Battery Level (%)" />
          </div>
        }
      >
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={schedule} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="hour" {...axisProps} />
              <YAxis yAxisId="left" {...axisProps} axisLine={false} unit=" MW" />
              <YAxis yAxisId="right" orientation="right" {...axisProps} axisLine={false} domain={[0, 100]} unit="%" />
              <Tooltip
                content={({ active, payload }) => {
                  const row = payload?.[0]?.payload;
                  if (!active || !row) return null;

                  const isIdle = row.charge_mw <= 0.01 && row.discharge_mw <= 0.01;
                  return (
                    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-lg text-xs">
                      <p className="font-semibold text-slate-900 mb-2">{row.hour}</p>
                      <p className="text-emerald-700">
                        Charging Power: {formatNumber(row.charge_mw, 2)} MW
                      </p>
                      <p className="text-blue-700">
                        Power Supplied: {formatNumber(row.discharge_mw, 2)} MW
                      </p>
                      <p className="text-violet-700">
                        Battery Level: {formatNumber(row.battery_soc_pct, 1)}%
                      </p>
                      <p className="text-slate-700">
                        Energy Remaining: {formatNumber(row.battery_energy_mwh, 2)} MWh
                      </p>
                      {isIdle && <p className="text-slate-500 mt-1">Battery is idle this hour.</p>}
                    </div>
                  );
                }}
              />
              <Bar yAxisId="left" dataKey="charge_mw" name="Charging Power (MW)" fill={COLORS.charge} />
              <Bar yAxisId="left" dataKey={(d) => -d.discharge_mw} name="Power Supplied (MW)" fill={COLORS.discharge} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="battery_soc_pct"
                name="Battery Level (%)"
                stroke="#7c3aed"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <ChartCard
        title="Electricity Grid Usage: With vs. Without Battery"
        description="Compare hourly grid power with and without the battery. Discharging can reduce grid use; charging can temporarily increase it. Solar generation is shown for context. Grid usage is based on modeled demand, not utility meter readings."
        legend={
          <div className="flex flex-wrap gap-4">
            <LegendItem color={COLORS.solar} label="Solar Power Generated" />
            <LegendItem color={COLORS.gridImport} label="Grid Usage Without Battery" />
            <LegendItem color={COLORS.managed} label="Grid Usage With Battery" />
          </div>
        }
      >
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={schedule} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="hour" {...axisProps} />
              <YAxis {...axisProps} axisLine={false} unit=" MW" />
              <Tooltip
                content={({ active, payload }) => {
                  const row = payload?.[0]?.payload;
                  if (!active || !row) return null;

                  return (
                    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-lg text-xs">
                      <p className="font-semibold text-slate-900 mb-2">{row.hour}</p>
                      <p className="text-amber-700">
                        Solar Power Generated: {formatNumber(row.solar_mw, 2)} MW
                      </p>
                      <p className="text-orange-700">
                        Grid Usage Without Battery: {formatNumber(row.unmanaged_import_mw, 2)} MW
                      </p>
                      <p className="text-teal-700">
                        Grid Usage With Battery: {formatNumber(row.managed_import_mw, 2)} MW
                      </p>
                    </div>
                  );
                }}
              />
              <Area
                type="monotone"
                dataKey="solar_mw"
                name="Solar Power Generated"
                fill={COLORS.solarFill}
                stroke={COLORS.solar}
              />
              <Line
                type="stepAfter"
                dataKey="unmanaged_import_mw"
                name="Grid Usage Without Battery"
                stroke={COLORS.gridImport}
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="stepAfter"
                dataKey="managed_import_mw"
                name="Grid Usage With Battery"
                stroke={COLORS.managed}
                strokeWidth={2.2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}
