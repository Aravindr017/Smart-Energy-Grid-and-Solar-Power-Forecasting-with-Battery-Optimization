import React from 'react';
import { Menu, Sun, Activity, Zap, RefreshCw, Compass, ShieldCheck } from 'lucide-react';

export default function TopBar({
  activeTab,
  plantInfo,
  onOpenMobileSidebar,
  onRefresh,
  isRefreshing,
}) {
  const tabTitles = {
    overview: 'Facility Telemetry & PV Power Generation',
    forecast: '24-Hour AI/ML Multi-Step Forecasting & Risk Bounds',
    battery: 'BESS Arbitrage Schedule & State-of-Charge Dynamics',
    savings: 'Time-of-Use (TOU) Tariff Arbitrage & Economic Calculator',
    data: 'Processed Inverter & Weather Telemetry Dataset',
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white/90 backdrop-blur-md border-b border-slate-200/80 shadow-2xs">
      <div className="h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
        {/* Left: Hamburger (mobile) & Breadcrumbs */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobileSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-orange-50 focus:outline-none"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-orange-600 uppercase tracking-wider">
                {plantInfo?.name.split('(')[0].trim() || 'Solar Facility'}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60 hidden sm:inline-flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                Grid Synchronized
              </span>
            </div>
            <h1 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
              {tabTitles[activeTab] || 'Solar Intelligence Platform'}
            </h1>
          </div>
        </div>

        {/* Right: Plant Specs & Status */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-3 text-xs text-slate-500 bg-orange-50/50 px-3 py-1.5 rounded-lg border border-orange-100">
            <span className="flex items-center gap-1 font-medium text-slate-700">
              <Sun className="w-3.5 h-3.5 text-amber-500" />
              {plantInfo?.rated_capacity_mw} MW Rated
            </span>
            <span className="text-slate-300">|</span>
            <span>{plantInfo?.elevation_m}m Elevation</span>
            <span className="text-slate-300">|</span>
            <span>22 Inverters</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg text-slate-500 hover:text-orange-600 hover:bg-orange-50 border border-slate-200/70 transition-colors"
            title="Refresh telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-orange-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
