import React from 'react';
import {
  Sun,
  BatteryCharging,
  TrendingUp,
  DollarSign,
  Database,
  Activity,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Zap,
  MapPin,
  X,
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  plantId,
  setPlantId,
  plants,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
  optData,
}) {
  const currentPlant = plants.find((p) => p.id === plantId) || plants[0];
  const kpis = optData?.kpis || {};

  const navItems = [
    { id: 'overview', label: 'Plant Overview', icon: Sun },
    { id: 'forecast', label: 'Solar Forecasting', icon: TrendingUp },
    { id: 'battery', label: 'Battery Dispatch & SoC', icon: BatteryCharging },
    { id: 'savings', label: 'Tariff Savings Calculator', icon: DollarSign },
    { id: 'data', label: 'Data Records', icon: Database },
  ];

  const handleNavClick = (id) => {
    setActiveTab(id);
    if (setMobileOpen) setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 lg:hidden transition-opacity"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-white/95 backdrop-blur-md border-r border-slate-200/90 shadow-sm transition-all duration-300 ease-in-out ${
          mobileOpen ? 'translate-x-0 w-72' : '-translate-x-full lg:translate-x-0'
        } ${collapsed ? 'lg:w-20' : 'lg:w-72'}`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200/80">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 min-w-10 rounded-xl bg-gradient-to-br from-amber-500 via-orange-500 to-orange-600 flex items-center justify-center text-white shadow-sm ring-2 ring-orange-200/50">
              <Sun className="w-5 h-5" />
            </div>
            {(!collapsed || mobileOpen) && (
              <div className="flex flex-col truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-slate-900 tracking-tight text-base">
                    HeliosGrid
                  </span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-orange-100/80 text-orange-800">
                    BESS
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 truncate font-normal">
                  Solar & Energy Arbitrage
                </span>
              </div>
            )}
          </div>

          {/* Close button for Mobile */}
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Collapse Toggle for Desktop */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 border border-slate-200/60 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Facility Selector */}
        {(!collapsed || mobileOpen) ? (
          <div className="p-4 border-b border-slate-100 bg-orange-50/40">
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
              Select Solar Facility
            </label>
            <div className="relative">
              <select
                value={plantId}
                onChange={(e) => setPlantId(Number(e.target.value))}
                className="w-full bg-white text-xs font-semibold text-slate-800 border border-slate-200 rounded-lg px-3 py-2 pr-8 shadow-2xs focus:outline-none focus:ring-1 focus:ring-orange-500 cursor-pointer"
              >
                {plants.map((p) => (
                  <option key={p.id} value={p.id}>
                    Plant {p.id}: {p.name.split('(')[0].trim()} ({p.rated_capacity_mw} MW)
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-slate-500">
              <MapPin className="w-3.5 h-3.5 text-orange-500 shrink-0" />
              <span className="truncate">{currentPlant?.location_name || 'Andhra Pradesh, India'}</span>
            </div>
          </div>
        ) : (
          <div className="p-2 border-b border-slate-100 flex justify-center">
            <button
              onClick={() => setPlantId(plantId === 1 ? 2 : 1)}
              className="w-10 h-10 rounded-lg bg-orange-50 border border-orange-200 flex flex-col items-center justify-center text-xs font-bold text-orange-700 hover:bg-orange-100"
              title={`Switch to Plant ${plantId === 1 ? 2 : 1}`}
            >
              P{plantId}
            </button>
          </div>
        )}

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-orange-50/60'
                } ${collapsed && !mobileOpen ? 'justify-center px-0' : ''}`}
                title={collapsed && !mobileOpen ? item.label : undefined}
              >
                <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                {(!collapsed || mobileOpen) && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Quick System Telemetry in Sidebar */}
        {(!collapsed || mobileOpen) && (
          <div className="p-3 mx-3 mb-3 rounded-xl bg-gradient-to-br from-slate-50 to-orange-50/50 border border-orange-100/80 shadow-2xs">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                PuLP Optimizer
              </span>
              <span className="text-[10px] text-emerald-700 font-mono">CBC 2.10</span>
            </div>
            <div className="space-y-1.5 text-[11px] text-slate-600">
              <div className="flex justify-between">
                <span>Daily Savings:</span>
                <span className="font-bold text-emerald-700 font-mono">
                  ${(kpis.net_arbitrage_savings || 1695.47).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Self-Consumption:</span>
                <span className="font-semibold text-slate-800 font-mono">
                  {(kpis.solar_self_consumption_with_bess_pct || 48.5).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span>Inverters Active:</span>
                <span className="font-semibold text-slate-800">22 / 22 Online</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer info in sidebar */}
        {(!collapsed || mobileOpen) && (
          <div className="px-4 py-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Week 3 MVP Frozen</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">v1.0.0</span>
          </div>
        )}
      </aside>
    </>
  );
}
