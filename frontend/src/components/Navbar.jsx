import React from 'react';
import { Sun, BatteryCharging, TrendingUp, DollarSign, Database, Activity } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, plantId, setPlantId, plants, isRefreshing, onRefresh }) {
  const currentPlant = plants.find(p => p.id === plantId) || plants[0];

  const navItems = [
    { id: 'overview', label: 'Plant Overview', icon: Sun },
    { id: 'forecast', label: 'Solar Forecasting', icon: TrendingUp },
    { id: 'battery', label: 'Battery Dispatch & SoC', icon: BatteryCharging },
    { id: 'savings', label: 'Tariff Savings Calculator', icon: DollarSign },
    { id: 'data', label: 'Data Records', icon: Database },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white shadow-sm">
              <Sun className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900 tracking-tight text-base sm:text-lg">
                  HeliosGrid
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-orange-50 text-orange-700 border border-orange-200">
                  Solar & BESS Platform
                </span>
              </div>
              <p className="text-xs text-slate-500 font-normal">
                AI Forecasting & PuLP Battery Dispatch Optimization
              </p>
            </div>
          </div>

          {/* Plant Selector & System Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-medium">LP Solver Ready</span>
            </div>

            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg p-1">
              <span className="text-xs text-slate-500 pl-2 font-medium">Facility:</span>
              <select
                value={plantId}
                onChange={(e) => setPlantId(Number(e.target.value))}
                className="bg-white text-xs font-medium text-slate-800 border border-slate-200 rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-orange-500"
              >
                {plants.map((p) => (
                  <option key={p.id} value={p.id}>
                    Plant {p.id}: {p.name.split('(')[0].trim()} ({p.rated_capacity_mw} MW)
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 border-t border-slate-100 overflow-x-auto py-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-orange-700 bg-orange-50/80 border-b-2 border-orange-500'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-orange-600' : 'text-slate-400'}`} />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
