import React from 'react';
import {
  Sun,
  BatteryCharging,
  TrendingUp,
  DollarSign,
  Database,
  CloudRain,
  Leaf,
  FileText,
  ChevronLeft,
  ChevronRight,
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
}) {
  const currentPlant = plants.find((p) => p.id === plantId) || plants[0];
  const expanded = !collapsed || mobileOpen;

  const groups = [
    {
      label: 'Operations',
      items: [
        { id: 'overview', label: 'Overview', icon: Sun },
        { id: 'forecast', label: 'Solar Forecast', icon: TrendingUp },
        { id: 'battery', label: 'Battery Schedule', icon: BatteryCharging },
      ],
    },
    {
      label: 'Analysis',
      items: [
        { id: 'savings', label: 'Electricity Cost & Savings', icon: DollarSign },
        { id: 'data', label: 'Duck Curve & Data', icon: Database },
        { id: 'weather', label: 'Weather Scenarios', icon: CloudRain },
        { id: 'carbon', label: 'Environmental Benefits', icon: Leaf },
      ],
    },
    {
      label: 'Reporting',
      items: [{ id: 'report', label: 'Executive Report', icon: FileText }],
    },
  ];

  const handleNavClick = (id) => {
    setActiveTab(id);
    if (setMobileOpen) setMobileOpen(false);
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-navy-950/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col overflow-hidden bg-navy-900 text-slate-200 transition-all duration-300 ease-in-out ${
          mobileOpen ? 'translate-x-0 w-72' : '-translate-x-full lg:translate-x-0'
        } ${collapsed ? 'lg:w-20' : 'lg:w-72'}`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-white/10">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 min-w-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white">
              <Sun className="w-5 h-5" aria-hidden="true" />
            </div>
            {expanded && (
              <div className="flex flex-col truncate">
                <span className="font-semibold text-white tracking-tight">SOLARIS</span>
                <span className="text-[11px] text-slate-400">Energy analytics</span>
              </div>
            )}
          </div>

          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {expanded ? (
          <div className="p-4 border-b border-white/10">
            <label htmlFor="plant-select" className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Solar plant
            </label>
            <select
              id="plant-select"
              value={plantId}
              onChange={(e) => setPlantId(Number(e.target.value))}
              className="w-full bg-navy-800 text-xs font-semibold text-white border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
            >
              {plants.map((p) => (
                <option key={p.id} value={p.id}>
                  Plant {p.id}: {p.name.split('(')[0].trim()} ({p.rated_capacity_mw} MW)
                </option>
              ))}
            </select>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-slate-400">
              <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="truncate">{currentPlant?.location_name || 'Andhra Pradesh, India'}</span>
            </div>
          </div>
        ) : (
          <div className="p-2 border-b border-white/10 flex justify-center">
            <button
              onClick={() => setPlantId(plantId === 1 ? 2 : 1)}
              className="w-10 h-10 rounded-lg bg-navy-800 border border-white/10 flex items-center justify-center text-xs font-bold text-emerald-300 hover:bg-navy-700"
              title={`Switch to Plant ${plantId === 1 ? 2 : 1}`}
            >
              P{plantId}
            </button>
          </div>
        )}

        <nav className="flex-1 min-h-0 overflow-hidden px-3 py-4 space-y-4" aria-label="Main">
          {groups.map((group) => (
            <div key={group.label}>
              {expanded && (
                <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {group.label}
                </p>
              )}
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(item.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-emerald-600 text-white'
                          : 'text-slate-300 hover:text-white hover:bg-white/5'
                      } ${collapsed && !mobileOpen ? 'justify-center px-0' : ''}`}
                      title={collapsed && !mobileOpen ? item.label : undefined}
                    >
                      <Icon className="w-5 h-5 shrink-0" />
                      {expanded && <span>{item.label}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className={`shrink-0 border-t border-white/10 flex justify-center items-center ${expanded ? 'px-3 py-4' : 'px-1 py-3'}`}>
          <img
            src="/solaris-logo.png"
            alt="SOLARIS"
            className={`object-contain ${expanded ? 'w-56 h-40' : 'w-16 h-16'}`}
          />
        </div>
      </aside>
    </>
  );
}
