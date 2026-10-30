import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import { Sun, CloudSun, Wind, Zap, CheckCircle2 } from 'lucide-react';
import PageHeader from './ui/PageHeader';
import MetricCard from './ui/MetricCard';
import ChartCard from './ui/ChartCard';
import FilterBar from './ui/FilterBar';
import LoadingState from './ui/LoadingState';
import EmptyState from './ui/EmptyState';
import InfoTooltip from './ui/InfoTooltip';
import StatusBadge from './ui/StatusBadge';
import { COLORS, tooltipStyle, axisProps, formatNumber } from './ui/chartTheme';

export default function ForecastView({ data, loading }) {
  const [forecastMode, setForecastMode] = useState('live24h');
  const [visibleModels, setVisibleModels] = useState({
    actual: true,
    lightgbm: true,
    xgboost: true,
    prophet: true,
    ridge: false,
    persistence: false,
    bounds: true,
  });
  const [horizonLength, setHorizonLength] = useState(48);

  if (loading && !data) {
    return <LoadingState label="Loading forecast results…" />;
  }

  if (!data) {
    return (
      <EmptyState
        title="Forecast data is unavailable"
        description="The forecasting service did not return predictions for this plant."
      />
    );
  }

  const {
    metrics = [],
    predictions = [],
    feature_importance = [],
    bounds_info,
    live_24h_forecast,
  } = data;

  const filteredPredictions = predictions.slice(-horizonLength);
  const hasActual = filteredPredictions.some((row) => row.actual != null && Number(row.actual) !== 0);

  const toggleModel = (key) => {
    setVisibleModels((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleLeaderboardModel = (key) => {
    setVisibleModels((prev) => ({
      ...prev,
      [key]: forecastMode === 'benchmark' ? !prev[key] : true,
    }));
    setForecastMode('benchmark');
  };

  const getModelKey = (modelName) => {
    const name = String(modelName).toLowerCase();
    if (name.includes('lightgbm')) return 'lightgbm';
    if (name.includes('xgboost')) return 'xgboost';
    if (name.includes('prophet')) return 'prophet';
    if (name.includes('ridge')) return 'ridge';
    if (name.includes('persistence')) return 'persistence';
    return null;
  };

  const layers = [
    { key: 'actual', label: 'Measured generation', color: COLORS.actual },
    { key: 'lightgbm', label: 'LightGBM forecast', color: COLORS.lightgbm },
    { key: 'xgboost', label: 'XGBoost forecast', color: COLORS.xgboost },
    { key: 'prophet', label: 'Prophet', color: COLORS.prophet },
    { key: 'ridge', label: 'Ridge Regression', color: COLORS.ridge },
    { key: 'persistence', label: 'Persistence', color: COLORS.persistence },
    { key: 'bounds', label: '90% interval', color: COLORS.bounds },
  ];

  const liveTimeline = live_24h_forecast?.timeline || [];
  const liveKpis = live_24h_forecast?.kpis || {};
  const isLiveActive = forecastMode === 'live24h' && liveTimeline.length > 0;

  // Next upcoming day forecast data formatted for charts
  const liveChartData = liveTimeline.map((step) => ({
    time: step.time_label,
    timestamp: step.timestamp,
    lightgbm: step.lightgbm_kw,
    xgboost: step.xgboost_kw,
    prophet: step.prophet_kw,
    selected: step.selected_solar_kw,
    lower_bound: step.lower_bound_kw,
    upper_bound: step.upper_bound_kw,
    ghi: step.ghi_wm2,
    temp: step.ambient_temp_c,
    cloud: step.cloud_cover_pct,
  }));

  const activeWeatherData = liveChartData.find((d) => d.ghi > 0) || liveChartData[0] || {};

  return (
    <div className="page-stack">
      <PageHeader
        title="Solar generation forecast"
        description="Day-ahead solar forecasting powered by live Open-Meteo weather inputs and benchmarked against LightGBM, XGBoost, and Prophet models."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <FilterBar
              label="Mode"
              value={forecastMode}
              onChange={setForecastMode}
              options={[
                { id: 'live24h', label: 'Upcoming 24h (Live)' },
                { id: 'benchmark', label: '7-Day Benchmark' },
              ]}
            />
            {forecastMode === 'benchmark' && (
              <FilterBar
                label="Show"
                value={horizonLength}
                onChange={setHorizonLength}
                options={[
                  { id: 24, label: '24 hours' },
                  { id: 48, label: '48 hours' },
                  { id: 96, label: '4 days' },
                ]}
              />
            )}
          </div>
        }
      />

      {/* Mode 1: Upcoming 24-Hour Live Weather Forecast */}
      {isLiveActive && (
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-emerald-50/70 border border-emerald-200/60 rounded-xl text-xs text-emerald-900">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold">
                {live_24h_forecast.is_live_weather ? 'Live Weather Integration Active' : 'Offline Historical Weather Fallback'}
              </span>
              <span className="text-emerald-700">
                · Source: {live_24h_forecast.data_source} ({live_24h_forecast.forecast_start} to {live_24h_forecast.forecast_end})
              </span>
            </div>
            <span className="text-[11px] text-emerald-600">Updated: {live_24h_forecast.retrieved_at}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="24h Projected Energy"
              value={formatNumber(liveKpis.total_predicted_energy_mwh, 2)}
              unit="MWh"
              subtitle={`Peak ${formatNumber(liveKpis.peak_predicted_kw, 0)} kW · ${liveKpis.daylight_hours || 11} daylight hrs`}
              icon={Sun}
              tone="amber"
              badge={{ label: 'Day-Ahead', tone: 'success' }}
            />
            <MetricCard
              label="Forecast Solar Irradiance"
              value={formatNumber(activeWeatherData.ghi || 0, 0)}
              unit="W/m²"
              subtitle="Global horizontal irradiance (GHI)"
              icon={CloudSun}
              tone="orange"
            />
            <MetricCard
              label="Ambient Temperature"
              value={formatNumber(activeWeatherData.temp || 30, 1)}
              unit="°C"
              subtitle={`Cloud cover: ${Math.round(activeWeatherData.cloud || 0)}%`}
              icon={Zap}
              tone="blue"
            />
            <MetricCard
              label="Primary Forecaster"
              value="LightGBM"
              unit="(GBDT)"
              subtitle="90% uncertainty bound enforced"
              icon={CheckCircle2}
              tone="emerald"
              badge={{ label: 'Champion', tone: 'success' }}
            />
          </div>

          <ChartCard
            title="Upcoming 24-Hour Day-Ahead Solar Forecast"
            description="Operational day-ahead trajectory comparing LightGBM, XGBoost, and Prophet with physical zero night-time truncation."
          >
            <div className="h-96 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={liveChartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="time" {...axisProps} />
                  <YAxis
                    {...axisProps}
                    axisLine={false}
                    tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
                    label={{ value: 'kW', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
                  />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="upper_bound"
                    stroke="none"
                    fill={COLORS.bounds}
                    fillOpacity={0.45}
                    name="Upper bound (90%)"
                  />
                  <Area
                    type="monotone"
                    dataKey="lower_bound"
                    stroke="none"
                    fill="#ffffff"
                    fillOpacity={1}
                    name="Lower bound"
                  />
                  {visibleModels.lightgbm && (
                    <Line
                      type="monotone"
                      dataKey="lightgbm"
                      name="LightGBM (kW)"
                      stroke={COLORS.lightgbm}
                      strokeWidth={2.4}
                      dot={{ r: 3 }}
                    />
                  )}
                  {visibleModels.xgboost && (
                    <Line
                      type="monotone"
                      dataKey="xgboost"
                      name="XGBoost (kW)"
                      stroke={COLORS.xgboost}
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  )}
                  {visibleModels.prophet && (
                    <Line
                      type="monotone"
                      dataKey="prophet"
                      name="Prophet (kW)"
                      stroke={COLORS.prophet}
                      strokeWidth={1.8}
                      strokeDasharray="3 3"
                      dot={false}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </section>
      )}

      {/* Mode 2: Historical Out-of-Sample Benchmark */}
      {(!isLiveActive || forecastMode === 'benchmark') && (
        <section className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {layers.map((layer) => (
              <button
                key={layer.key}
                type="button"
                onClick={() => toggleModel(layer.key)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                  visibleModels[layer.key]
                    ? 'bg-white text-slate-800 border-slate-300'
                    : 'bg-slate-100 text-slate-400 border-transparent'
                }`}
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: layer.color }} />
                {layer.label}
              </button>
            ))}
          </div>

          {!hasActual && (
            <p className="text-xs text-amber-800 bg-amber-50 rounded-xl px-3 py-2">
              Measured generation is zero or missing for parts of this horizon, so comparison is limited.
            </p>
          )}

          <ChartCard
            title="Out-of-Sample Model Benchmark Chart"
            description={bounds_info?.methodology || 'Prediction interval with night-time output truncated at zero.'}
          >
            <div className="h-96 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={filteredPredictions} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="time" {...axisProps} />
                  <YAxis
                    {...axisProps}
                    axisLine={false}
                    tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
                    label={{ value: 'kW', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
                  />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  {visibleModels.bounds && (
                    <Area type="monotone" dataKey="upper_bound" stroke="none" fill={COLORS.bounds} fillOpacity={0.55} name="Upper bound (90%)" />
                  )}
                  {visibleModels.bounds && (
                    <Area type="monotone" dataKey="lower_bound" stroke="none" fill="#ffffff" fillOpacity={1} name="Lower bound" />
                  )}
                  {visibleModels.actual && (
                    <Line type="monotone" dataKey="actual" name="Measured (kW)" stroke={COLORS.actual} strokeWidth={2.4} dot={false} />
                  )}
                  {visibleModels.lightgbm && (
                    <Line type="monotone" dataKey="lightgbm" name="LightGBM (kW)" stroke={COLORS.lightgbm} strokeWidth={2} dot={false} />
                  )}
                  {visibleModels.xgboost && (
                    <Line type="monotone" dataKey="xgboost" name="XGBoost (kW)" stroke={COLORS.xgboost} strokeWidth={1.8} dot={false} />
                  )}
                  {visibleModels.prophet && (
                    <Line type="monotone" dataKey="prophet" name="Prophet (kW)" stroke={COLORS.prophet} strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                  )}
                  {visibleModels.ridge && (
                    <Line type="monotone" dataKey="ridge" name="Ridge (kW)" stroke={COLORS.ridge} strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                  )}
                  {visibleModels.persistence && (
                    <Line type="monotone" dataKey="persistence" name="Persistence (kW)" stroke={COLORS.persistence} strokeWidth={1.2} strokeDasharray="2 2" dot={false} />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </section>
      )}

      {/* Model Benchmark Comparison Table (Required: LightGBM, XGBoost, Prophet, Baselines) */}
      <section className="surface-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Model Comparison Leaderboard</h3>
            <p className="text-xs text-slate-500">
              Select one or more model names to show their actual out-of-sample forecasts on the chart. Metrics use chronological daylight hours (GHI &gt; 0).
            </p>
          </div>
          <StatusBadge tone="measured">Evaluated</StatusBadge>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-2.5 pr-4 font-medium">Model</th>
                <th className="py-2.5 pr-4 font-medium">
                  <span className="inline-flex items-center gap-1">
                    Daylight RMSE
                    <InfoTooltip label="Explain RMSE">Daylight root mean square error (kW). Lower is better.</InfoTooltip>
                  </span>
                </th>
                <th className="py-2.5 pr-4 font-medium">
                  <span className="inline-flex items-center gap-1">
                    Daylight MAPE
                    <InfoTooltip label="Explain MAPE">Daylight mean absolute percentage error (%). Lower is better.</InfoTooltip>
                  </span>
                </th>
                <th className="py-2.5 pr-4 font-medium">Daylight MAE (kW)</th>
                <th className="py-2.5 pr-4 font-medium">
                  <span className="inline-flex items-center gap-1">
                    Daylight R²
                    <InfoTooltip label="Explain R2">Share of daytime variance explained.</InfoTooltip>
                  </span>
                </th>
                <th className="py-2.5 pr-4 font-medium">Daylight nRMSE (%)</th>
                <th className="py-2.5 font-medium">Overall RMSE (kW)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {metrics.map((m, idx) => {
                const modelKey = getModelKey(m.model);
                const isSelected = String(m.model).toLowerCase().includes('lightgbm');
                const isXGB = String(m.model).toLowerCase().includes('xgboost');
                const isVisible = modelKey ? visibleModels[modelKey] : false;
                return (
                  <tr
                    key={idx}
                    className={`${isVisible ? 'bg-slate-50' : ''} ${isSelected ? 'border-l-2 border-l-emerald-500' : (isXGB ? 'border-l-2 border-l-orange-400' : '')}`}
                  >
                    <td className="py-3 pr-4 font-medium text-slate-900">
                      {modelKey ? (
                        <button
                          type="button"
                          onClick={() => toggleLeaderboardModel(modelKey)}
                          aria-pressed={isVisible}
                          className="inline-flex items-center gap-2 rounded text-left hover:text-emerald-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
                          title={`${isVisible ? 'Remove' : 'Show'} ${m.model} forecast on the chart`}
                        >
                          <span
                            className={`inline-flex h-4 w-4 items-center justify-center rounded border text-[10px] ${
                              isVisible ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-slate-300 text-transparent'
                            }`}
                            aria-hidden="true"
                          >
                            ✓
                          </span>
                          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[modelKey] }} />
                          {m.model}
                        </button>
                      ) : m.model}
                      {isSelected && (
                        <StatusBadge tone="success" className="ml-2">
                          Primary
                        </StatusBadge>
                      )}
                      {isXGB && (
                        <StatusBadge tone="orange" className="ml-2">
                          Evaluated
                        </StatusBadge>
                      )}
                    </td>
                    <td className="py-3 pr-4 tabular-nums">{m.daylight_rmse_kw?.toLocaleString()}</td>
                    <td className="py-3 pr-4 tabular-nums">{m.daylight_mape_pct?.toFixed(2)}%</td>
                    <td className="py-3 pr-4 tabular-nums">{m.daylight_mae_kw?.toLocaleString()}</td>
                    <td className="py-3 pr-4 tabular-nums font-semibold text-emerald-700">{m.daylight_r2?.toFixed(4)}</td>
                    <td className="py-3 pr-4 tabular-nums">{m.daylight_nrmse_pct?.toFixed(2)}%</td>
                    <td className="py-3 tabular-nums">{m.overall_rmse_kw?.toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <ChartCard
        title="Feature Importance Ranking"
        description="Relative importance of weather and solar geometry features in LightGBM."
      >
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={feature_importance} layout="vertical" margin={{ top: 5, right: 24, left: 88, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
              <XAxis type="number" {...axisProps} />
              <YAxis type="category" dataKey="feature" {...axisProps} axisLine={false} width={80} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="importance" fill={COLORS.solar} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}
