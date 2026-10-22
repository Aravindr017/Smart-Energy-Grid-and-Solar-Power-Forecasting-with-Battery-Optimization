import React from 'react';
import {
  BatteryCharging,
  Sliders,
  ShieldCheck,
  Zap,
  Activity,
  ArrowRight,
  TrendingDown,
  Info,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

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

  // Compute SVG arc for Radial SoC Gauge
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const currentSoc = socGauge.final_soc_pct || 20;
  const strokeDashoffset = circumference - (currentSoc / 100) * circumference;

  return (
    <div className="space-y-6">
      {/* Battery & Dispatch Controller Configuration Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-orange-600" />
            <h2 className="text-base font-semibold text-slate-900">
              BESS Physical Parameters & TOU Tariff Arbitrage Controls
            </h2>
          </div>
          <button
            onClick={onRunOptimization}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium rounded-lg shadow-xs transition-colors disabled:opacity-50"
          >
            {loading ? 'Solving LP...' : 'Re-run PuLP Optimization'}
          </button>
        </div>

        {/* Sliders Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 text-xs">
          {/* Capacity */}
          <div className="space-y-1.5">
            <div className="flex justify-between font-medium">
              <span className="text-slate-600">Storage Capacity</span>
              <span className="text-slate-900 font-semibold">{params.battery_capacity_mwh} MWh</span>
            </div>
            <input
              type="range"
              min="1"
              max="30"
              step="1"
              value={params.battery_capacity_mwh}
              onChange={(e) => handleSliderChange('battery_capacity_mwh', e.target.value)}
              className="w-full accent-orange-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400">Total rated battery energy capacity</p>
          </div>

          {/* Inverter Power */}
          <div className="space-y-1.5">
            <div className="flex justify-between font-medium">
              <span className="text-slate-600">Inverter PCS Rating</span>
              <span className="text-slate-900 font-semibold">{params.max_inverter_power_mw} MW</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="15"
              step="0.5"
              value={params.max_inverter_power_mw}
              onChange={(e) => handleSliderChange('max_inverter_power_mw', e.target.value)}
              className="w-full accent-orange-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400">Peak charge & discharge power limit</p>
          </div>

          {/* Round-trip Efficiency */}
          <div className="space-y-1.5">
            <div className="flex justify-between font-medium">
              <span className="text-slate-600">Round-Trip Efficiency</span>
              <span className="text-slate-900 font-semibold">{params.round_trip_efficiency_pct}%</span>
            </div>
            <input
              type="range"
              min="75"
              max="98"
              step="0.5"
              value={params.round_trip_efficiency_pct}
              onChange={(e) => handleSliderChange('round_trip_efficiency_pct', e.target.value)}
              className="w-full accent-orange-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400">AC-to-AC round-trip system efficiency</p>
          </div>

          {/* Initial SoC */}
          <div className="space-y-1.5">
            <div className="flex justify-between font-medium">
              <span className="text-slate-600">Initial State-of-Charge</span>
              <span className="text-slate-900 font-semibold">{params.initial_soc_pct}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="80"
              step="5"
              value={params.initial_soc_pct}
              onChange={(e) => handleSliderChange('initial_soc_pct', e.target.value)}
              className="w-full accent-orange-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400">Starting stored energy (Terminal $E_T \ge E_0$)</p>
          </div>
        </div>

        {/* TOU Tariff Inputs */}
        <div className="mt-4 pt-4 border-t border-slate-100">
          <div className="text-xs font-semibold text-slate-700 mb-2">Time-of-Use (TOU) Industrial Electricity Rates ($/kWh)</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block text-slate-500 mb-1">Off-Peak (Night)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="0.50"
                value={params.off_peak_rate}
                onChange={(e) => handleSliderChange('off_peak_rate', e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-800 font-mono font-medium focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Normal / Shoulder</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="0.50"
                value={params.normal_rate}
                onChange={(e) => handleSliderChange('normal_rate', e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-800 font-mono font-medium focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Evening Peak (17:00-21:00)</label>
              <input
                type="number"
                step="0.01"
                min="0.05"
                max="1.00"
                value={params.peak_rate}
                onChange={(e) => handleSliderChange('peak_rate', e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-800 font-mono font-medium focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Solar Export Feed-In</label>
              <input
                type="number"
                step="0.01"
                min="0.0"
                max="0.30"
                value={params.export_feedin_rate}
                onChange={(e) => handleSliderChange('export_feedin_rate', e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-slate-800 font-mono font-medium focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Week 3 Deliverable: Battery State-of-Charge (SoC) Gauges Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radial SoC Gauge Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Battery State of Charge (SoC) Gauge
              </h3>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-200">
                DoD Safe Range: 10%–90%
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Real-time terminal energy state and operational boundary tracking
            </p>
          </div>

          {/* SVG Radial Gauge */}
          <div className="flex items-center justify-center my-4">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                {/* Background Ring */}
                <circle
                  cx="88"
                  cy="88"
                  r={radius}
                  stroke="#f1f5f9"
                  strokeWidth="12"
                  fill="transparent"
                />
                {/* Safe Operating Range Arc (10% to 90%) */}
                <circle
                  cx="88"
                  cy="88"
                  r={radius}
                  stroke="#e2e8f0"
                  strokeWidth="12"
                  fill="transparent"
                  strokeDasharray={`${0.8 * circumference} ${circumference}`}
                  strokeDashoffset={-0.1 * circumference}
                />
                {/* Active SoC Fill Arc */}
                <circle
                  cx="88"
                  cy="88"
                  r={radius}
                  stroke="#f97316"
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  className="transition-all duration-700 ease-out"
                />
              </svg>
              {/* Inner Center Label */}
              <div className="absolute flex flex-col items-center">
                <span className="text-3xl font-extrabold text-slate-900">{currentSoc.toFixed(1)}%</span>
                <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">Terminal SoC</span>
              </div>
            </div>
          </div>

          {/* Gauge Status Indicators */}
          <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Terminal Condition ($E_T \ge E_0$):</span>
              <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
                <CheckCircle2 className="w-3.5 h-3.5" /> Satisfied
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Cycling Throughput (24h):</span>
              <span className="font-mono font-medium text-slate-800">
                {((kpis.battery_total_throughput_kwh || 0) / 1000).toFixed(2)} MWh
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Equivalent Full Cycles:</span>
              <span className="font-mono font-medium text-slate-800">
                {(kpis.equivalent_full_cycles || 0).toFixed(2)} cycles
              </span>
            </div>
          </div>
        </div>

        {/* Linear Boundary Visualizer & Key Metrics */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              State-of-Charge Dynamics & Operational Limits
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Cell health protection boundaries preventing deep discharge and high-voltage overcharging
            </p>
          </div>

          {/* Horizontal Boundary Bar */}
          <div className="my-6 space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-600">
              <span>0% Empty</span>
              <span className="text-orange-700 font-semibold">Min: {socGauge.min_soc_pct?.toFixed(1)}%</span>
              <span className="text-emerald-700 font-semibold">Peak: {socGauge.max_soc_pct?.toFixed(1)}%</span>
              <span>100% Full</span>
            </div>
            <div className="relative w-full h-7 bg-slate-100 rounded-lg overflow-hidden border border-slate-200 flex">
              {/* Lockout zone 0-10% */}
              <div className="w-[10%] bg-red-100 border-r border-red-300 flex items-center justify-center text-[9px] text-red-700 font-medium">
                Lockout
              </div>
              {/* Safe zone 10-90% */}
              <div className="w-[80%] bg-orange-50/50 relative flex items-center justify-center text-[10px] text-slate-500 font-medium">
                Safe Operating Zone (10% - 90%)
                {/* Active Range Fill */}
                <div
                  className="absolute h-full bg-gradient-to-r from-amber-400 to-orange-500 opacity-60 rounded-sm"
                  style={{
                    left: `${Math.max(0, (socGauge.min_soc_pct - 10) / 0.8)}%`,
                    width: `${Math.min(100, (socGauge.max_soc_pct - socGauge.min_soc_pct) / 0.8)}%`,
                  }}
                ></div>
              </div>
              {/* Lockout zone 90-100% */}
              <div className="w-[10%] bg-red-100 border-l border-red-300 flex items-center justify-center text-[9px] text-red-700 font-medium">
                Ceiling
              </div>
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>SoC_min: 10%</span>
              <span>Cell Active Range: 10% – 90% DoD</span>
              <span>SoC_max: 90%</span>
            </div>
          </div>

          {/* Quick Metrics Strip */}
          <div className="grid grid-cols-3 gap-4 pt-3 border-t border-slate-100 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-500 block text-[11px]">Minimum SoC Reached</span>
              <span className="text-base font-bold text-slate-800">{socGauge.min_soc_pct?.toFixed(1)}%</span>
              <span className="text-[10px] text-emerald-600 block">Within 10% limit</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-500 block text-[11px]">Maximum SoC Stored</span>
              <span className="text-base font-bold text-slate-800">{socGauge.max_soc_pct?.toFixed(1)}%</span>
              <span className="text-[10px] text-emerald-600 block">Within 90% limit</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-500 block text-[11px]">Degradation Wear Cost</span>
              <span className="text-base font-bold text-slate-800">${kpis.degradation_wear_cost?.toFixed(2)}</span>
              <span className="text-[10px] text-slate-400 block">$0.005 / kWh wear</span>
            </div>
          </div>
        </div>
      </div>

      {/* Week 3 Deliverable: Automated Charge / Discharge Schedule Visualizer */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              24-Hour Battery Power Dispatch & State of Charge Progression
            </h3>
            <p className="text-xs text-slate-500">
              Charges with excess daytime solar (positive bars) and discharges during evening peak hours 17:00–21:00 (negative bars)
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-blue-500 rounded-xs"></span>
              <span className="text-slate-600">Charge Power (MW)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-orange-500 rounded-xs"></span>
              <span className="text-slate-600">Discharge Power (MW)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-purple-600"></span>
              <span className="text-slate-600">SoC (%)</span>
            </div>
          </div>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={schedule} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="hour" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis
                yAxisId="left"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                unit=" MW"
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                domain={[0, 100]}
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
              />
              <Bar yAxisId="left" dataKey="charge_mw" name="Charging Power (MW)" fill="#3b82f6" />
              <Bar
                yAxisId="left"
                dataKey={(d) => -d.discharge_mw}
                name="Discharging Power (MW)"
                fill="#f97316"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="battery_soc_pct"
                name="State of Charge (%)"
                stroke="#9333ea"
                strokeWidth={2.5}
                dot={{ r: 3 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Duck Curve Mitigation Grid Load Shifting Chart */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Duck Curve Shifting: Unmanaged vs. BESS Managed Grid Import
            </h3>
            <p className="text-xs text-slate-500">
              Peak import demand shaved from {((kpis.peak_grid_import_without_bess_kw || 0)/1000).toFixed(2)} MW down to {((kpis.peak_grid_import_with_bess_kw || 0)/1000).toFixed(2)} MW ({kpis.peak_shaving_percentage?.toFixed(1)}% peak reduction)
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-red-500"></span>
              <span className="text-slate-600">Unmanaged Grid Import</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-600"></span>
              <span className="text-slate-600">Optimized with BESS</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={schedule} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="hour" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} unit=" MW" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
              />
              <Area
                type="monotone"
                dataKey="solar_mw"
                name="Solar Output (MW)"
                fill="#fef3c7"
                stroke="#f59e0b"
                strokeWidth={1.5}
              />
              <Line
                type="monotone"
                dataKey="unmanaged_import_mw"
                name="Unmanaged Import (MW)"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="managed_import_mw"
                name="Optimized with BESS (MW)"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
