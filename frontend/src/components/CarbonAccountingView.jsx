import React, { useState, useEffect } from 'react';
import { Leaf, Info } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
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
import StatusBadge from './ui/StatusBadge';
import { COLORS, tooltipStyle, axisProps, formatNumber } from './ui/chartTheme';

export default function CarbonAccountingView({ plantId = 1 }) {
  const [data, setData] = useState(null);
  const [emissionFactor, setEmissionFactor] = useState(0.716);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const presets = [
    { label: 'Cleaner Electricity', factor: 0.5, desc: 'Example of a grid with more hydro or nuclear power' },
    { label: "India's Average Electricity Emissions", factor: 0.716, desc: 'CEA national average for 2024' },
    { label: 'Thermal Power Emissions', factor: 0.82, desc: 'Emissions from fossil-fuel power plants' },
    { label: 'Coal-Heavy Electricity', factor: 0.95, desc: 'Example of a grid with more coal power' },
  ];

  const getFactorLabel = (row) =>
    presets.find((preset) => Math.abs(preset.factor - row.grid_emission_factor_kg_per_kwh) < 0.005)?.label
    || row.factor_label;

  const fetchCarbonData = (factor) => {
    setLoading(true);
    setError(null);
    const efQuery = factor != null ? `&emission_factor=${factor}` : '';
    fetch(`/api/carbon?plant_id=${plantId}${efQuery}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load carbon accounting data`);
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Carbon accounting fetch error:', err);
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCarbonData(emissionFactor);
  }, [plantId]);

  const handleFactorChange = (newFactor) => {
    setEmissionFactor(newFactor);
    fetchCarbonData(newFactor);
  };

  const provenance = data?.provenance || {};
  const sensitivity = data?.sensitivity_summary || [];
  const weatherCarbon = data?.weather_scenarios_carbon || [];
  const custom = data?.custom_calculation;

  const activeBaseline =
    sensitivity.find((s) => Math.abs(s.grid_emission_factor_kg_per_kwh - emissionFactor) < 0.005) ||
    sensitivity[1] ||
    {};

  const dailyAvoidedTonnes = custom?.total_avoided_co2_tonnes ?? activeBaseline.total_avoided_co2_tonnes;
  const storageAvoidedTonnes = custom?.storage_avoided_co2_tonnes ?? activeBaseline.storage_avoided_co2_tonnes;
  const annualAvoidedTonnes = custom?.annual_projected_avoided_co2_tonnes ?? activeBaseline.annual_projected_avoided_co2_tonnes;
  const reductionPct = custom?.emissions_reduction_pct ?? activeBaseline.emissions_reduction_pct;

  if (loading && !data) {
    return <LoadingState label="Loading carbon estimates…" />;
  }

  if (error) {
    return <ErrorState title="Carbon estimates could not be loaded" message={error} onRetry={() => fetchCarbonData(emissionFactor)} />;
  }

  const comparisonData = sensitivity.map((row) => ({
    name: getFactorLabel(row),
    tonnes: Number(row.total_avoided_co2_tonnes),
  }));

  return (
    <div className="page-stack">
      <PageHeader
        title="Carbon Emission Savings"
        description="Estimated CO₂ emissions avoided by using solar power and shifting battery use. These are estimates, not certified carbon offsets."
        actions={<StatusBadge tone="estimated">Estimates only</StatusBadge>}
      />

      <div className="flex items-start gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-xs text-emerald-900">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <p>
          Electricity pollution level means the emissions linked to each unit of grid electricity. Source:{' '}
          {provenance.source || 'Central Electricity Authority (CEA), Govt of India'}. The default is{' '}
          <strong>0.716 kg CO2e / kWh</strong>, India's average electricity emissions for 2024. CO₂ savings are estimates
          based on electricity displaced by solar and battery use; manufacturing emissions are not included.
        </p>
      </div>

      <section className="surface-card p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold text-slate-900">Electricity Pollution Level</h3>
          <span className="font-mono text-sm font-semibold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-lg">
            {emissionFactor.toFixed(3)} kg CO2e / kWh
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {presets.map((p) => {
            const isSelected = Math.abs(p.factor - emissionFactor) < 0.005;
            return (
              <button
                key={p.label}
                onClick={() => handleFactorChange(p.factor)}
                className={`text-left p-3 rounded-xl border ${
                  isSelected ? 'border-emerald-600 bg-emerald-50' : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <p className="text-xs font-semibold text-slate-900">{p.label}</p>
                <p className="text-sm font-mono mt-1">{p.factor.toFixed(3)}</p>
                <p className="text-[11px] text-slate-500 mt-1">{p.desc}</p>
              </button>
            );
          })}
        </div>
        <input
          type="range"
          min="0.30"
          max="1.20"
          step="0.005"
          value={emissionFactor}
          onChange={(e) => handleFactorChange(parseFloat(e.target.value))}
          className="range-control"
          aria-label="Electricity pollution level"
        />
        <div className="flex justify-between text-[11px] text-slate-400 mt-1">
          <span>0.30 kg/kWh</span>
          <span>1.20 kg/kWh</span>
        </div>
      </section>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="CO₂ Emissions Avoided"
          value={dailyAvoidedTonnes != null ? formatNumber(dailyAvoidedTonnes, 2) : '—'}
          unit="t / day"
          subtitle="Estimated daily savings from solar and battery use"
          icon={Leaf}
          tone="emerald"
          badge={{ label: 'Estimated', tone: 'estimated' }}
        />
        <MetricCard
          label="Extra CO₂ Saved by Battery"
          value={storageAvoidedTonnes != null ? formatNumber(storageAvoidedTonnes, 2) : '—'}
          unit="t / day"
          subtitle="Estimated additional savings from battery use"
          tone="teal"
        />
        <MetricCard
          label="Reduction in CO₂ Emissions"
          value={reductionPct != null ? `${formatNumber(reductionPct, 1)}%` : '—'}
          subtitle="Compared with grid electricity at the selected pollution level"
          tone="navy"
        />
        <MetricCard
          label="Estimated Yearly CO₂ Savings"
          value={annualAvoidedTonnes != null ? formatNumber(annualAvoidedTonnes, 0) : '—'}
          unit="t"
          subtitle="Based on 365 similar days; an estimate, not a certified total"
          tone="amber"
        />
      </div>

      {comparisonData.length > 0 && (
        <ChartCard
          title="CO₂ Savings Under Different Electricity Sources"
          description="Compare estimated CO₂ savings at different electricity pollution levels. Select a level above to update the estimates."
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis {...axisProps} axisLine={false} unit=" t" />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="tonnes" name="CO₂ avoided (tonnes)" fill={COLORS.managed} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      )}

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">Compare Electricity Pollution Levels</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Select a row to see how the estimated savings change. Estimates use the current optimization day.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Electricity source</th>
                <th className="py-3 px-4">Pollution level (kg/kWh)</th>
                <th className="py-3 px-4">Extra CO₂ saved by battery (t/day)</th>
                <th className="py-3 px-4">CO₂ emissions avoided (t/day)</th>
                <th className="py-3 px-4">CO₂ reduction</th>
                <th className="py-3 px-4">Estimated yearly savings (t)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sensitivity.map((row) => {
                const isSelected = Math.abs(row.grid_emission_factor_kg_per_kwh - emissionFactor) < 0.005;
                return (
                  <tr
                    key={row.factor_label}
                    onClick={() => handleFactorChange(row.grid_emission_factor_kg_per_kwh)}
                    className={`cursor-pointer ${isSelected ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}
                  >
                    <td className="py-3 px-4 font-medium">{getFactorLabel(row)}</td>
                    <td className="py-3 px-4 font-mono">{formatNumber(row.grid_emission_factor_kg_per_kwh, 3)}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(row.storage_avoided_co2_tonnes, 2)}</td>
                    <td className="py-3 px-4 tabular-nums font-semibold">{formatNumber(row.total_avoided_co2_tonnes, 2)}</td>
                    <td className="py-3 px-4 text-emerald-700">{formatNumber(row.emissions_reduction_pct, 1)}%</td>
                    <td className="py-3 px-4 tabular-nums">{Number(row.annual_projected_avoided_co2_tonnes).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {weatherCarbon.length > 0 && (
        <section className="surface-card overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">CO₂ Savings Under Different Weather Conditions</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Estimates use India's average electricity emissions of 0.716 kg/kWh.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Scenario</th>
                  <th className="py-3 px-4">Solar power generated (MWh)</th>
                  <th className="py-3 px-4">Extra CO₂ saved by battery (t/day)</th>
                  <th className="py-3 px-4">CO₂ emissions avoided (t/day)</th>
                  <th className="py-3 px-4">Estimated yearly savings (t)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {weatherCarbon.map((sc) => (
                  <tr key={sc.scenario_name} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-medium">{sc.scenario_label}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(sc.total_solar_generation_mwh, 1)}</td>
                    <td className="py-3 px-4 tabular-nums">{formatNumber(sc.storage_avoided_co2_tonnes, 2)}</td>
                    <td className="py-3 px-4 tabular-nums text-emerald-800 font-semibold">{formatNumber(sc.total_avoided_co2_tonnes, 2)}</td>
                    <td className="py-3 px-4 tabular-nums">{Number(sc.annual_projected_avoided_co2_tonnes).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
