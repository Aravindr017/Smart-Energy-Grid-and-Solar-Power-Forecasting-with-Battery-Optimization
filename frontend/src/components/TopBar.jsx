import React from 'react';
import { Menu, Moon, Sun, RefreshCw } from 'lucide-react';

const TAB_COPY = {
  overview: {
    title: 'Executive overview',
    subtitle: 'Plant generation, forecast, battery, and estimated savings at a glance',
  },
  forecast: {
    title: 'Solar forecasting',
    subtitle: 'Predicted generation compared with measured output',
  },
  battery: {
    title: 'Battery optimization',
    subtitle: 'Charge, discharge, and state of charge over the next day',
  },
  savings: {
    title: 'Electricity Cost & Savings',
    subtitle: 'Compare estimated electricity costs with and without a battery',
  },
  data: {
    title: 'Duck curve & data',
    subtitle: 'Solar versus the demand profile, plus plant telemetry records',
  },
  weather: {
    title: 'Weather & extreme scenarios',
    subtitle: 'How generation and battery results change under stress cases',
  },
  carbon: {
    title: 'Carbon Emission Savings',
    subtitle: 'Estimated CO₂ emissions avoided through solar and battery use',
  },
  report: {
    title: 'Executive report',
    subtitle: 'Generate and download a PDF summary of the current analysis',
  },
};

export default function TopBar({
  activeTab,
  plantInfo,
  onOpenMobileSidebar,
  onRefresh,
  isRefreshing,
  isDarkTheme,
  onToggleTheme,
}) {
  const copy = TAB_COPY[activeTab] || TAB_COPY.overview;
  const plantName = plantInfo?.name?.split('(')[0].trim() || 'Solar facility';

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
      <div className="px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onOpenMobileSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="min-w-0">
            <p className="text-xs font-medium text-emerald-700 truncate">{plantName}</p>
            <h1 className="text-base sm:text-lg font-semibold text-slate-900 truncate">{copy.title}</h1>
            <p className="hidden sm:block text-xs text-slate-500 truncate">{copy.subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-3 text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-xl">
            <span className="inline-flex items-center gap-1 font-medium text-slate-700">
              <Sun className="w-3.5 h-3.5 text-solar-500" />
              {plantInfo?.rated_capacity_mw} MW
            </span>
            <span className="text-slate-300">|</span>
            <span>{plantInfo?.inverters_count || 22} inverters</span>
          </div>

          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 border border-slate-200"
            title={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
            aria-label={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
            aria-pressed={isDarkTheme}
          >
            {isDarkTheme ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 border border-slate-200"
            title="Refresh data"
            aria-label="Refresh data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-700' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
