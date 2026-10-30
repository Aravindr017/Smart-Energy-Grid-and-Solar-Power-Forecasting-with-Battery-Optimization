import React, { useState, useEffect } from 'react';
import { Download, Calendar } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import PageHeader from './ui/PageHeader';
import MetricCard from './ui/MetricCard';
import ChartCard from './ui/ChartCard';
import LoadingState from './ui/LoadingState';
import SecondaryButton from './ui/SecondaryButton';
import LegendItem from './ui/LegendItem';
import StatusBadge from './ui/StatusBadge';
import { COLORS, tooltipStyle, axisProps, formatNumber } from './ui/chartTheme';

export default function DataExplorerView({ plantId }) {
  const [duckData, setDuckData] = useState(null);
  const [selectedDate, setSelectedDate] = useState('2020-05-15');
  const [loadingDuck, setLoadingDuck] = useState(true);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loadingDataset, setLoadingDataset] = useState(true);

  useEffect(() => {
    setLoadingDuck(true);
    fetch(`/api/duck-curve?date=${selectedDate}`)
      .then((res) => res.json())
      .then((data) => {
        setDuckData(data);
        if (data.selected_date && data.selected_date !== selectedDate) {
          setSelectedDate(data.selected_date);
        }
        setLoadingDuck(false);
      })
      .catch((err) => {
        console.error('Failed to load duck curve:', err);
        setLoadingDuck(false);
      });
  }, [selectedDate]);

  useEffect(() => {
    setLoadingDataset(true);
    fetch(`/api/dataset?plant_id=${plantId}&limit=50`)
      .then((res) => res.json())
      .then((data) => {
        setDatasetInfo(data);
        setLoadingDataset(false);
      })
      .catch((err) => {
        console.error('Failed to load dataset:', err);
        setLoadingDataset(false);
      });
  }, [plantId]);

  const handleDownloadDataset = () => {
    if (!datasetInfo?.records?.length) return;
    const cols = datasetInfo.columns;
    const rows = datasetInfo.records.map((r) => cols.map((c) => r[c]));
    const csvContent = 'data:text/csv;charset=utf-8,' + [cols.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `plant_${plantId}_hourly_processed_dataset.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const duckMetrics = duckData?.metrics || {};
  const duckTimeseries = duckData?.timeseries || [];

  return (
    <div className="page-stack">
      <PageHeader
        title="Duck curve"
        description="Midday solar can push net grid demand down, then demand rises quickly as the sun sets. The demand profile is illustrative, not measured city or utility load."
        actions={
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <Calendar className="w-4 h-4" />
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="input-control !w-auto !py-1.5"
            >
              {duckData?.available_dates?.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              )) || <option value="2020-05-15">2020-05-15</option>}
            </select>
          </label>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Peak demand"
          value={formatNumber(duckMetrics.peak_grid_demand_mw, 1)}
          unit="MW"
          subtitle="Illustrative substation profile"
          tone="orange"
        />
        <MetricCard
          label="Midday solar"
          value={formatNumber(duckMetrics.max_midday_solar_mw, 1)}
          unit="MW"
          subtitle="Combined plant generation"
          tone="amber"
          badge={{ label: 'Measured', tone: 'measured' }}
        />
        <MetricCard
          label="Lowest net load"
          value={formatNumber(duckMetrics.min_midday_net_load_mw, 1)}
          unit="MW"
          subtitle={`Belly drop ${formatNumber(duckMetrics.belly_depth_drop_mw, 1)} MW`}
          tone="teal"
        />
        <MetricCard
          label="Evening ramp"
          value={`+${formatNumber(duckMetrics.evening_ramp_rate_mw_per_hour, 1)}`}
          unit="MW/h"
          subtitle="17:00–21:00 demand ramp"
          tone="navy"
        />
      </div>

      <ChartCard
        title={`Solar, demand, and net load (${selectedDate})`}
        description="Daytime solar fills the belly of the curve. The evening ramp is the steep rise after sunset."
        legend={
          <div className="flex flex-wrap gap-4">
            <LegendItem color={COLORS.solar} label="Solar generation" />
            <LegendItem color={COLORS.demand} label="Grid demand" dashed />
            <LegendItem color={COLORS.netLoad} label="Net load" />
          </div>
        }
      >
        <div className="h-80 w-full">
          {loadingDuck ? (
            <LoadingState label="Loading duck curve…" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={duckTimeseries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="time_label" {...axisProps} interval={7} />
                <YAxis {...axisProps} axisLine={false} unit=" MW" />
                <Tooltip contentStyle={tooltipStyle} />
                <Area
                  type="monotone"
                  dataKey="solar_generation_mw"
                  name="Solar generation (MW)"
                  fill={COLORS.solarFill}
                  stroke={COLORS.solar}
                />
                <Line
                  type="monotone"
                  dataKey="grid_demand_mw"
                  name="Grid demand (MW)"
                  stroke={COLORS.demand}
                  strokeWidth={1.75}
                  strokeDasharray="4 4"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="net_load_mw"
                  name="Net load (MW)"
                  stroke={COLORS.netLoad}
                  strokeWidth={2.4}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </ChartCard>

      <section className="surface-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Plant {plantId} telemetry sample</h3>
            <p className="text-xs text-slate-500 mt-1">Hourly processed records used by forecasting and optimization.</p>
          </div>
          <SecondaryButton onClick={handleDownloadDataset} disabled={loadingDataset}>
            <Download className="w-4 h-4" />
            Download sample CSV
          </SecondaryButton>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Hourly rows</p>
            <p className="text-lg font-semibold">{datasetInfo?.total_rows ?? '—'}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Inverters</p>
            <p className="text-lg font-semibold">22</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Sample size</p>
            <p className="text-lg font-semibold">{datasetInfo?.records?.length ?? '—'} rows</p>
          </div>
        </div>

        {loadingDataset ? (
          <LoadingState label="Loading dataset rows…" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 text-slate-600 font-sans font-semibold border-y border-slate-200">
                <tr>
                  {datasetInfo?.columns?.map((c) => (
                    <th key={c} className="py-2.5 px-3 whitespace-nowrap">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {datasetInfo?.records?.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    {datasetInfo.columns.map((c) => (
                      <td key={c} className="py-2 px-3 text-slate-700 whitespace-nowrap">
                        {typeof row[c] === 'number' ? row[c].toFixed(2) : String(row[c] || '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-3">
          <StatusBadge tone="measured">Plant telemetry</StatusBadge>
        </div>
      </section>
    </div>
  );
}
