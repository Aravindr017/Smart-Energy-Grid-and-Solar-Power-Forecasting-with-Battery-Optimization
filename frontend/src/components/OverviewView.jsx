import React, { useState } from 'react';
import { Sun, Zap, Thermometer, Compass, Calendar, Activity, BarChart2 } from 'lucide-react';
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
} from 'recharts';

export default function OverviewView({ data, plantInfo, granularity, setGranularity, loading }) {
  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-8 h-8 border-4 border-orange-200 border-t-orange-600 rounded-full animate-spin"></div>
        <span className="ml-3 text-sm text-slate-600">Loading solar generation telemetry...</span>
      </div>
    );
  }

  const { kpis, timeseries } = data;

  return (
    <div className="space-y-6">
      {/* Facility Metadata Strip */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {plantInfo ? plantInfo.name : 'Solar PV Power Station'}
            </h2>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
              <span>Location: {plantInfo?.location_name || 'Andhra Pradesh, India'}</span>
              <span>•</span>
              <span>Coordinates: {plantInfo?.latitude}° N, {plantInfo?.longitude}° E</span>
              <span>•</span>
              <span>Elevation: {plantInfo?.elevation_m} m</span>
              <span>•</span>
              <span>Inverter Architecture: {plantInfo?.inverters_count} Units</span>
            </div>
          </div>

          {/* Granularity Switcher */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Resolution:</span>
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs">
              {[
                { id: 'hourly', label: 'Hourly' },
                { id: '15min_plant', label: '15-Min Plant' },
                { id: '15min', label: '15-Min Inverter' },
              ].map((res) => (
                <button
                  key={res.id}
                  onClick={() => setGranularity(res.id)}
                  className={`px-3 py-1 font-medium rounded-md transition-all ${
                    granularity === res.id
                      ? 'bg-white text-orange-700 shadow-xs border border-slate-200/60'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {res.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Total Generation</span>
            <Zap className="w-4 h-4 text-orange-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {kpis.total_energy_mwh.toLocaleString()} <span className="text-sm font-normal text-slate-500">MWh</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Cumulative yield across observation span</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Peak AC Capacity</span>
            <Sun className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {kpis.peak_ac_kw.toLocaleString()} <span className="text-sm font-normal text-slate-500">kW</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Maximum instantaneous inverter power</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Mean Active Power</span>
            <Activity className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {kpis.avg_ac_kw.toLocaleString()} <span className="text-sm font-normal text-slate-500">kW</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Time-averaged output power</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Observation Range</span>
            <Calendar className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 text-base font-semibold text-slate-900">
            {kpis.date_start} to {kpis.date_end}
          </div>
          <p className="mt-1 text-xs text-slate-500">{kpis.total_records.toLocaleString()} validated timesteps</p>
        </div>
      </div>

      {/* Main Chart: AC Generation vs Global Horizontal Irradiance */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              AC Power Output vs. Solar Irradiance (GHI)
            </h3>
            <p className="text-xs text-slate-500">
              Correlating active power generation with solar irradiation telemetry
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs bg-orange-500"></span>
              <span className="text-slate-600 font-medium">AC Power (kW)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t-2 border-dashed border-amber-500"></span>
              <span className="text-slate-600 font-medium">GHI (W/m²)</span>
            </div>
          </div>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeseries} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis
                yAxisId="left"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${(val / 1000).toFixed(1)}k`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                }}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="ac_power_kw"
                name="AC Power (kW)"
                fill="#ffedd5"
                stroke="#f97316"
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="ghi"
                name="GHI (W/m²)"
                stroke="#d97706"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Module vs Ambient Thermal Dynamics */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Photovoltaic Thermal Dynamics
            </h3>
            <p className="text-xs text-slate-500">
              Module back-of-panel temperature tracking vs. ambient weather temperature
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-red-500 rounded-full"></span>
              <span className="text-slate-600">Module Temp (°C)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-blue-500 rounded-full"></span>
              <span className="text-slate-600">Ambient Temp (°C)</span>
            </div>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeseries} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} unit="°C" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  fontSize: '0.75rem',
                }}
              />
              <Line
                type="monotone"
                dataKey="module_temp_c"
                name="Module Temp (°C)"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="ambient_temp_c"
                name="Ambient Temp (°C)"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
