import React, { useState, useEffect } from 'react';
import {
  CloudRain,
  Sun,
  CloudLightning,
  TrendingDown,
  ShieldAlert,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import PageHeader from './ui/PageHeader';
import MetricCard from './ui/MetricCard';
import ChartCard from './ui/ChartCard';
import LoadingState from './ui/LoadingState';
import ErrorState from './ui/ErrorState';
import SecondaryButton from './ui/SecondaryButton';
import StatusBadge from './ui/StatusBadge';
import { COLORS, tooltipStyle, axisProps, formatNumber } from './ui/chartTheme';

const SCENARIO_LABELS = {
  normal: 'Normal Weather',
  heavy_cloud: 'Cloudy Weather',
  monsoon_prolonged: 'Heavy Rain / Monsoon',
  sudden_drop: 'Sudden Solar Drop',
  multi_day_low: 'Low Sunlight for Several Days',
  recovery: 'Weather Improving',
};

const SCENARIO_DESCRIPTIONS = {
  normal: 'Normal sunny or partly cloudy conditions.',
  heavy_cloud: 'Heavy clouds reduce solar power generation.',
  monsoon_prolonged: 'Heavy rain and monsoon weather reduce solar power.',
  sudden_drop: 'Solar power suddenly decreases due to bad weather.',
  multi_day_low: 'Continuous cloudy weather reduces solar generation for days.',
  recovery: 'Solar power gradually returns after bad weather.',
};

export default function WeatherStressView({ plantId = 1 }) {
  const [data, setData] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState('normal');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStressData = () => {
    setLoading(true);
    setError(null);
    fetch(`/api/weather-stress?plant_id=${plantId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load weather stress data`);
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Weather stress fetch error:', err);
        setError(
          err.message === 'Failed to fetch'
            ? 'Cannot reach the SOLARIS API. Start the backend on port 8000, then try again.'
            : err.message
        );
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchStressData();
  }, [plantId]);

  const summary = data?.summary || [];
  const currentSummary = summary.find((s) => s.scenario_name === selectedScenario) || summary[0] || {};
  const baseline = summary.find((s) => s.scenario_name === 'normal') || summary[0] || {};
  const scenariosMeta = data?.scenarios_metadata || [];

  const getScenarioIcon = (name) => {
    switch (name) {
      case 'normal':
        return <Sun className="w-5 h-5 text-solar-600" />;
      case 'heavy_cloud':
        return <CloudRain className="w-5 h-5 text-slate-500" />;
      case 'monsoon_prolonged':
        return <CloudLightning className="w-5 h-5 text-blue-600" />;
      case 'sudden_drop':
        return <TrendingDown className="w-5 h-5 text-orange-600" />;
      case 'multi_day_low':
        return <ShieldAlert className="w-5 h-5 text-amber-600" />;
      case 'recovery':
        return <Sun className="w-5 h-5 text-emerald-600" />;
      default:
        return <CloudRain className="w-5 h-5 text-slate-500" />;
    }
  };

  if (loading && !data) {
    return <LoadingState label="Loading weather scenarios…" />;
  }

  if (error) {
    return <ErrorState title="Weather scenarios could not be loaded" message={error} onRetry={fetchStressData} />;
  }

  const comparison = summary.map((row) => ({
    name: SCENARIO_LABELS[row.scenario_name] || row.scenario_label,
    solar: Number(row.total_solar_generation_7d_mwh),
    savings: Number(row.net_arbitrage_savings),
  }));

  return (
    <div className="page-stack">
      <PageHeader
        title="Weather and extreme-weather scenarios"
        description="Select a plant, then a scenario. Results below compare weather stress cases with the normal baseline from the existing stress suite."
        actions={
          <SecondaryButton onClick={fetchStressData}>
            <RefreshCw className="w-4 h-4" />
            Refresh scenarios
          </SecondaryButton>
        }
      />

      <ol className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-xs text-slate-600">
        {['Select the plant in the sidebar', 'Review the available period', 'Choose a scenario', 'Refresh if needed', 'Compare results'].map(
          (step, i) => (
            <li key={step} className="rounded-xl bg-white border border-slate-200 px-3 py-2">
              <span className="font-semibold text-emerald-700">{i + 1}.</span> {step}
            </li>
          )
        )}
      </ol>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {scenariosMeta.map((sc) => {
          const isSelected = selectedScenario === sc.name;
          return (
            <button
              key={sc.name}
              onClick={() => setSelectedScenario(sc.name)}
              className={`text-left p-3.5 rounded-2xl border transition-colors ${
                isSelected ? 'bg-emerald-50 border-emerald-600' : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              {getScenarioIcon(sc.name)}
              <p className="text-xs font-semibold text-slate-900 mt-2">{SCENARIO_LABELS[sc.name] || sc.label}</p>
              <p className="text-[11px] text-slate-500 mt-1">{SCENARIO_DESCRIPTIONS[sc.name] || sc.description}</p>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusBadge tone={selectedScenario === 'normal' ? 'measured' : 'info'}>
          {selectedScenario === 'normal' ? 'Baseline scenario' : 'Weather scenario'}
        </StatusBadge>
        <StatusBadge tone="info">Plant {plantId}</StatusBadge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Solar generation (24h)"
          value={currentSummary.total_solar_generation_mwh != null ? formatNumber(currentSummary.total_solar_generation_mwh, 1) : '—'}
          unit="MWh"
          subtitle={`7-day peak ${formatNumber(currentSummary.peak_actual_generation_kw, 0)} kW`}
          tone="amber"
        />
        <MetricCard
          label="Estimated 24-hour battery savings"
          value={currentSummary.net_arbitrage_savings != null ? `₹${formatNumber(currentSummary.net_arbitrage_savings, 0)}` : '—'}
          subtitle={`Throughput ${formatNumber(currentSummary.battery_throughput_mwh, 2)} MWh`}
          tone="emerald"
          badge={{ label: 'Estimated', tone: 'estimated' }}
        />
        <MetricCard
          label="Grid dependence (24h)"
          value={currentSummary.grid_dependency_pct != null ? `${formatNumber(currentSummary.grid_dependency_pct, 1)}%` : '—'}
          subtitle={`Autonomy ${formatNumber(currentSummary.storage_autonomy_pct, 1)}%`}
          tone="orange"
        />
        <MetricCard
          label="7-day daylight RMSE"
          value={currentSummary.lgb_daylight_rmse_kw != null ? formatNumber(currentSummary.lgb_daylight_rmse_kw, 1) : '—'}
          unit="kW"
          subtitle={`Ridge ${formatNumber(currentSummary.ridge_daylight_rmse_kw, 1)} kW`}
          tone="navy"
        />
      </div>

      <ChartCard
        title="Baseline versus scenario"
        description={`Normal 7-day generation ${formatNumber(baseline.total_solar_generation_7d_mwh, 1)} MWh compared with each stress case. Weather-stress values are simulated.`}
      >
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparison} margin={{ top: 8, right: 8, left: 0, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="name" {...axisProps} interval={0} angle={-18} textAnchor="end" height={60} />
              <YAxis {...axisProps} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Bar dataKey="solar" name="Solar (MWh)" fill={COLORS.solar} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">Scenario comparison</h3>
          <p className="text-xs text-slate-500 mt-0.5">Click a row to inspect that case. Values are scenario estimates compared against the normal baseline.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Scenario</th>
                <th className="py-3 px-4">Solar (7-day MWh)</th>
                <th className="py-3 px-4">Peak (7-day kW)</th>
                <th className="py-3 px-4">Ridge RMSE (7-day kW)</th>
                <th className="py-3 px-4">LightGBM RMSE (7-day kW)</th>
                <th className="py-3 px-4">Net savings (24h ₹)</th>
                <th className="py-3 px-4">Grid dependence (24h)</th>
                <th className="py-3 px-4">Autonomy (24h)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.map((row) => {
                const isSelected = row.scenario_name === selectedScenario;
                return (
                  <tr
                    key={row.scenario_name}
                    onClick={() => setSelectedScenario(row.scenario_name)}
                    className={`cursor-pointer ${isSelected ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {getScenarioIcon(row.scenario_name)}
                        <span className="font-medium">{SCENARIO_LABELS[row.scenario_name] || row.scenario_label}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.total_solar_generation_7d_mwh, 1)}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.peak_actual_generation_kw, 0)}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.ridge_daylight_rmse_kw, 1)}</td>
                    <td className="py-3 px-4 tabular-nums text-emerald-700">{formatNumber(row.lgb_daylight_rmse_kw, 1)}</td>
                    <td className="py-3 px-4 tabular-nums">₹{formatNumber(row.net_arbitrage_savings, 0)}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.grid_dependency_pct, 1)}%</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.storage_autonomy_pct, 1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
