import React, { useState } from 'react';
import { TrendingUp, ShieldCheck, Layers, Info, CheckSquare, Square } from 'lucide-react';
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

export default function ForecastView({ data, loading }) {
  const [visibleModels, setVisibleModels] = useState({
    actual: true,
    lightgbm: true,
    prophet: true,
    ridge: false,
    persistence: false,
    bounds: true,
  });

  const [horizonLength, setHorizonLength] = useState(48);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-8 h-8 border-4 border-orange-200 border-t-orange-600 rounded-full animate-spin"></div>
        <span className="ml-3 text-sm text-slate-600">Loading forecast benchmarks & model predictions...</span>
      </div>
    );
  }

  const { metrics, predictions, feature_importance, bounds_info } = data;
  const filteredPredictions = predictions.slice(-horizonLength);

  const toggleModel = (key) => {
    setVisibleModels((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-6">
      {/* Forecast Header Strip */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">
                24-Hour Solar Generation Forecasting
              </h2>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                LightGBM + Prophet
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Multi-step 24h horizon predictions with statistical forecast bounds (90% prediction confidence interval)
            </p>
          </div>

          {/* Horizon Window Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Forecast Horizon:</span>
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs">
              {[
                { count: 24, label: '24 Hours' },
                { count: 48, label: '48 Hours' },
                { count: 96, label: '4 Days' },
              ].map((h) => (
                <button
                  key={h.count}
                  onClick={() => setHorizonLength(h.count)}
                  className={`px-3 py-1 font-medium rounded-md transition-all ${
                    horizonLength === h.count
                      ? 'bg-white text-orange-700 shadow-xs border border-slate-200/60'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Model Toggles & Legend Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-4 mt-4 border-t border-slate-100 text-xs">
          <span className="font-medium text-slate-500 mr-1">Layer Visibility:</span>

          {/* Actual Power */}
          <button
            onClick={() => toggleModel('actual')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.actual
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-slate-900 border border-white"></span>
            Actual Generation
          </button>

          {/* LightGBM */}
          <button
            onClick={() => toggleModel('lightgbm')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.lightgbm
                ? 'bg-emerald-600 text-white border-emerald-600'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            LightGBM (GBDT)
          </button>

          {/* Prophet */}
          <button
            onClick={() => toggleModel('prophet')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.prophet
                ? 'bg-purple-600 text-white border-purple-600'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-purple-300"></span>
            Prophet (Additive)
          </button>

          {/* Ridge */}
          <button
            onClick={() => toggleModel('ridge')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.ridge
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-300"></span>
            Ridge Regression
          </button>

          {/* Persistence */}
          <button
            onClick={() => toggleModel('persistence')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.persistence
                ? 'bg-slate-500 text-white border-slate-500'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-slate-300"></span>
            Persistence (24h Lag)
          </button>

          {/* Forecast Bounds */}
          <button
            onClick={() => toggleModel('bounds')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-colors ${
              visibleModels.bounds
                ? 'bg-amber-100 text-amber-900 border-amber-300'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            <span className="w-2 h-2 rounded-xs bg-amber-400"></span>
            Forecast Bounds (90% CI)
          </button>
        </div>
      </div>

      {/* Main Interactive Forecast Chart with Bounds */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Multi-Model Forecast Curves with Uncertainty Bounds
            </h3>
            <p className="text-xs text-slate-500">
              Shaded envelope represents 90% empirical prediction interval (±1.645 σ) with physical zero truncation
            </p>
          </div>
        </div>

        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={filteredPredictions} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(1)}k kW`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
              />

              {/* Shaded Forecast Bounds Area */}
              {visibleModels.bounds && (
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="#fef3c7"
                  fillOpacity={0.6}
                  name="Upper Bound (90% CI)"
                />
              )}
              {visibleModels.bounds && (
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stroke="none"
                  fill="#ffffff"
                  fillOpacity={1.0}
                  name="Lower Bound"
                />
              )}

              {/* Actual Power */}
              {visibleModels.actual && (
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual Power (kW)"
                  stroke="#0f172a"
                  strokeWidth={2.5}
                  dot={false}
                />
              )}

              {/* LightGBM Hero Model */}
              {visibleModels.lightgbm && (
                <Line
                  type="monotone"
                  dataKey="lightgbm"
                  name="LightGBM GBDT (kW)"
                  stroke="#059669"
                  strokeWidth={2.0}
                  dot={false}
                />
              )}

              {/* Prophet */}
              {visibleModels.prophet && (
                <Line
                  type="monotone"
                  dataKey="prophet"
                  name="Prophet (kW)"
                  stroke="#9333ea"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                />
              )}

              {/* Ridge */}
              {visibleModels.ridge && (
                <Line
                  type="monotone"
                  dataKey="ridge"
                  name="Ridge Regression (kW)"
                  stroke="#2563eb"
                  strokeWidth={1.5}
                  strokeDasharray="3 3"
                  dot={false}
                />
              )}

              {/* Persistence Benchmark */}
              {visibleModels.persistence && (
                <Line
                  type="monotone"
                  dataKey="persistence"
                  name="Persistence 24h Lag (kW)"
                  stroke="#64748b"
                  strokeWidth={1.2}
                  strokeDasharray="2 2"
                  dot={false}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Benchmark Performance Metrics Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Evaluation Metrics Benchmark Matrix
            </h3>
            <p className="text-xs text-slate-500">
              Computed strictly during daytime active generation hours (GHI &gt; 0) to avoid zero-inflation bias
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md">
            Test Horizon Validation
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-y border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Forecasting Model</th>
                <th className="py-2.5 px-4">Daylight RMSE (kW)</th>
                <th className="py-2.5 px-4">Daylight MAPE (%)</th>
                <th className="py-2.5 px-4">Daylight MAE (kW)</th>
                <th className="py-2.5 px-4">Daylight R² Score</th>
                <th className="py-2.5 px-4">Daylight nRMSE (%)</th>
                <th className="py-2.5 px-4">Overall RMSE (kW)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {metrics.map((m, idx) => {
                const isHero = m.model.toLowerCase().includes('lightgbm');
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50 transition-colors ${
                      isHero ? 'bg-orange-50/40 font-medium' : ''
                    }`}
                  >
                    <td className="py-3 px-4 flex items-center gap-2">
                      <span className="text-slate-900 font-medium">{m.model}</span>
                      {isHero && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-100 text-orange-800 font-semibold">
                          Selected Model
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.daylight_rmse_kw.toLocaleString()}</td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.daylight_mape_pct.toFixed(2)}%</td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.daylight_mae_kw.toLocaleString()}</td>
                    <td className="py-3 px-4 font-mono font-semibold text-emerald-700">{m.daylight_r2.toFixed(4)}</td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.daylight_nrmse_pct.toFixed(2)}%</td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.overall_rmse_kw.toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Feature Importance Bar Chart */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">
          LightGBM Predictive Feature Importance
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Gini split gain contributions across meteorological and lagged telemetry features
        </p>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={feature_importance}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis
                type="category"
                dataKey="feature"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
              />
              <Bar dataKey="importance" fill="#f97316" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
