import React from 'react';
import { Sun, BatteryCharging, TrendingUp, DollarSign, Database } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, plantId, setPlantId, plants }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Sun },
    { id: 'forecast', label: 'Solar Forecast', icon: TrendingUp },
    { id: 'battery', label: 'Battery Schedule', icon: BatteryCharging },
    { id: 'savings', label: 'Tariff Savings', icon: DollarSign },
    { id: 'data', label: 'Duck Curve & Data', icon: Database },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-700 flex items-center justify-center text-white">
              <Sun className="w-5 h-5" />
            </div>
            <div>
              <span className="font-semibold text-slate-900">SOLARIS</span>
              <p className="text-xs text-slate-500">Energy analytics platform</p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg p-1">
            <label htmlFor="nav-plant" className="text-xs text-slate-500 pl-2 font-medium">
              Plant
            </label>
            <select
              id="nav-plant"
              value={plantId}
              onChange={(e) => setPlantId(Number(e.target.value))}
              className="bg-white text-xs font-medium text-slate-800 border border-slate-200 rounded px-2.5 py-1"
            >
              {plants.map((p) => (
                <option key={p.id} value={p.id}>
                  Plant {p.id}: {p.name.split('(')[0].trim()} ({p.rated_capacity_mw} MW)
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex space-x-1 overflow-x-auto py-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg whitespace-nowrap ${
                  isActive ? 'text-emerald-800 bg-emerald-50' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-700' : 'text-slate-400'}`} />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
