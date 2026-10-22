import React from 'react';
import {
  DollarSign,
  TrendingUp,
  Download,
  Calendar,
  PiggyBank,
  Zap,
  Clock,
  ArrowUpRight,
  ShieldAlert,
} from 'lucide-react';

export default function TariffSavingsView({ optData, params }) {
  const kpis = optData?.kpis || {};
  const financials = optData?.financials || {};
  const schedule = optData?.schedule || [];

  const handleDownloadCsv = () => {
    if (!schedule.length) return;
    const headers = [
      'Hour',
      'Step',
      'Tariff_Rate_USD_kWh',
      'Tariff_Tier',
      'Solar_Generation_MW',
      'Load_Demand_MW',
      'Unmanaged_Import_MW',
      'Managed_Import_MW',
      'BESS_Charge_MW',
      'BESS_Discharge_MW',
      'BESS_Energy_MWh',
      'BESS_SoC_Pct',
    ];
    const rows = schedule.map((r) => [
      r.hour,
      r.step,
      r.tariff_rate,
      r.tariff_tier,
      r.solar_mw,
      r.demand_mw,
      r.unmanaged_import_mw,
      r.managed_import_mw,
      r.charge_mw,
      r.discharge_mw,
      r.battery_energy_mwh,
      r.battery_soc_pct,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'bess_24h_optimal_dispatch_schedule.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header Strip */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-semibold text-slate-900">
                Net TOU Tariff Arbitrage & Economic Calculator
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Linear Programming cost minimization comparing unmanaged solar baseline vs. BESS time-shifting
            </p>
          </div>
          <button
            onClick={handleDownloadCsv}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-xs transition-colors"
          >
            <Download className="w-4 h-4 text-slate-500" />
            Export Dispatch Schedule (CSV)
          </button>
        </div>
      </div>

      {/* Primary Financial Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Daily Net Savings</span>
            <span className="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              +{kpis.savings_percentage?.toFixed(1)}% Cost Cut
            </span>
          </div>
          <div className="mt-2 text-3xl font-extrabold text-emerald-700">
            ${(kpis.net_arbitrage_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="mt-1 text-xs text-slate-500">Net TOU arbitrage gain per 24 hours</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Unmanaged Electricity Cost</span>
            <span className="text-xs text-slate-400">Baseline</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            ${(kpis.cost_without_bess || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="mt-1 text-xs text-slate-500">Grid imports without battery storage</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Optimized Cost with BESS</span>
            <span className="text-xs text-emerald-600 font-medium">Post-LP</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            ${(kpis.cost_with_bess || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="mt-1 text-xs text-slate-500">Including degradation wear wear cost</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Self-Consumption Gain</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {kpis.solar_self_consumption_with_bess_pct?.toFixed(1)}%
          </div>
          <p className="mt-1 text-xs text-emerald-600 font-medium">
            +{financials.solar_self_consumption_gain_pct}% from {kpis.solar_self_consumption_without_bess_pct?.toFixed(1)}% baseline
          </p>
        </div>
      </div>

      {/* Investment & Long-Term Financial ROI Projection */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">
          BESS Capital Expenditure & Simple Payback Horizon
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Annualized financial feasibility based on {params.battery_capacity_mwh} MWh nominal storage capacity
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-orange-50/50 border border-orange-100">
            <span className="text-slate-500 block">Annualized Arbitrage Savings</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">
              ${(financials.annual_savings_projected || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
            <span className="text-[11px] text-slate-400 mt-0.5 block">Estimated 365-day cycling revenue</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-500 block">Estimated System CAPEX</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">
              ${(financials.estimated_capex || 0).toLocaleString()}
            </span>
            <span className="text-[11px] text-slate-400 mt-0.5 block">At $250 / kWh all-in installed cost</span>
          </div>

          <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-100">
            <span className="text-emerald-800 font-medium block">Simple Amortization Payback</span>
            <span className="text-xl font-bold text-emerald-800 mt-1 block">
              {financials.simple_payback_years?.toFixed(1)} Years
            </span>
            <span className="text-[11px] text-emerald-600 mt-0.5 block">Break-even ROI without subsidies</span>
          </div>
        </div>
      </div>

      {/* 24-Hour Hour-by-Hour Dispatch Schedule Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Detailed 24-Hour Hour-by-Hour Optimal Dispatch Matrix
            </h3>
            <p className="text-xs text-slate-500">
              Hour-by-hour power balance, battery charge/discharge dispatch, and grid import state
            </p>
          </div>
          <span className="text-xs font-medium px-2.5 py-1 bg-slate-100 text-slate-600 rounded">
            24 Hourly Steps
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-y border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Hour</th>
                <th className="py-2.5 px-3">Tariff Tier</th>
                <th className="py-2.5 px-3">Rate ($/kWh)</th>
                <th className="py-2.5 px-3">Solar (MW)</th>
                <th className="py-2.5 px-3">Load (MW)</th>
                <th className="py-2.5 px-3">Charge (MW)</th>
                <th className="py-2.5 px-3">Discharge (MW)</th>
                <th className="py-2.5 px-3">Unmanaged Import</th>
                <th className="py-2.5 px-3">Optimized Import</th>
                <th className="py-2.5 px-3">Battery SoC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {schedule.map((row, idx) => {
                const isPeak = row.tariff_tier === 'Peak';
                const isCharging = row.charge_mw > 0.01;
                const isDischarging = row.discharge_mw > 0.01;

                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50 transition-colors ${
                      isPeak ? 'bg-orange-50/30' : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{row.hour}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-sans font-medium ${
                          isPeak
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : row.tariff_tier === 'Off-Peak'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {row.tariff_tier}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">${row.tariff_rate.toFixed(3)}</td>
                    <td className="py-2.5 px-3 text-amber-700">{row.solar_mw.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-slate-600">{row.demand_mw.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-blue-600 font-semibold">
                      {isCharging ? `+${row.charge_mw.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-orange-600 font-semibold">
                      {isDischarging ? `-${row.discharge_mw.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">{row.unmanaged_import_mw.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-emerald-700 font-semibold">{row.managed_import_mw.toFixed(2)}</td>
                    <td className="py-2.5 px-3 font-semibold text-purple-700">{row.battery_soc_pct.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
