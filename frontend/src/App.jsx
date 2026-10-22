import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OverviewView from './components/OverviewView';
import ForecastView from './components/ForecastView';
import BatteryScheduleView from './components/BatteryScheduleView';
import TariffSavingsView from './components/TariffSavingsView';
import DataExplorerView from './components/DataExplorerView';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [plantId, setPlantId] = useState(1);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [plants, setPlants] = useState([
    {
      id: 1,
      name: 'Plant 1 (Gandikota Solar Farm)',
      rated_capacity_mw: 29.5,
      location_name: 'Andhra Pradesh, India',
      latitude: 14.8,
      longitude: 78.18,
      elevation_m: 203,
      inverters_count: 22,
    },
    {
      id: 2,
      name: 'Plant 2 (Ananthapuramu Solar Park)',
      rated_capacity_mw: 26.2,
      location_name: 'Andhra Pradesh, India',
      latitude: 14.38,
      longitude: 77.5,
      elevation_m: 491,
      inverters_count: 22,
    },
  ]);

  const [granularity, setGranularity] = useState('hourly');
  const [overviewData, setOverviewData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [optData, setOptData] = useState(null);

  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(true);
  const [loadingOpt, setLoadingOpt] = useState(true);

  // Battery and Tariff Optimization Configuration Parameters
  const [params, setParams] = useState({
    plant_id: 1,
    battery_capacity_mwh: 10.0,
    max_inverter_power_mw: 5.0,
    round_trip_efficiency_pct: 90.25,
    initial_soc_pct: 20.0,
    off_peak_rate: 0.05,
    normal_rate: 0.1,
    peak_rate: 0.25,
    export_feedin_rate: 0.04,
    degradation_cost_per_kwh: 0.005,
    installed_cost_per_kwh: 250.0,
  });

  // Load facility list
  useEffect(() => {
    fetch('/api/plants')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setPlants(data);
        }
      })
      .catch(() => console.log('Using default plant metadata'));
  }, []);

  // Sync params with plantId
  useEffect(() => {
    setParams((prev) => ({ ...prev, plant_id: plantId }));
  }, [plantId]);

  // Load Overview Data
  const loadOverview = () => {
    setLoadingOverview(true);
    fetch(`/api/overview?plant_id=${plantId}&granularity=${granularity}&limit=72`)
      .then((res) => res.json())
      .then((data) => {
        setOverviewData(data);
        setLoadingOverview(false);
      })
      .catch((err) => {
        console.error('Failed to load overview:', err);
        setLoadingOverview(false);
      });
  };

  useEffect(() => {
    loadOverview();
  }, [plantId, granularity]);

  // Load Forecast Data
  const loadForecast = () => {
    setLoadingForecast(true);
    fetch(`/api/forecast?plant_id=${plantId}&slice_length=72`)
      .then((res) => res.json())
      .then((data) => {
        setForecastData(data);
        setLoadingForecast(false);
      })
      .catch((err) => {
        console.error('Failed to load forecast:', err);
        setLoadingForecast(false);
      });
  };

  useEffect(() => {
    loadForecast();
  }, [plantId]);

  // Run PuLP LP Optimization
  const runOptimization = () => {
    setLoadingOpt(true);
    fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
      .then((res) => res.json())
      .then((data) => {
        setOptData(data);
        setLoadingOpt(false);
      })
      .catch((err) => {
        console.error('Failed to run optimization:', err);
        setLoadingOpt(false);
      });
  };

  useEffect(() => {
    runOptimization();
  }, [plantId]);

  // Manual Refresh Handler
  const handleRefresh = () => {
    setIsRefreshing(true);
    loadOverview();
    loadForecast();
    runOptimization();
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const currentPlant = plants.find((p) => p.id === plantId) || plants[0];

  return (
    <div className="relative min-h-screen text-slate-800 font-sans antialiased overflow-x-hidden">
      {/* Light-colored Background with Solar Farm Image & Solar Gradient Veil */}
      <div
        className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat pointer-events-none transition-all duration-700"
        style={{
          backgroundImage: "url('/solar_farm_bg.jpg')",
        }}
      >
        {/* Soft white and light-orange luminous overlay for high contrast & elegance */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/94 via-orange-50/90 to-amber-50/85 backdrop-blur-[2px]" />
      </div>

      {/* Main Content Layout with Sidebar */}
      <div className="relative z-10 flex min-h-screen">
        {/* Responsive Sidebar */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          plantId={plantId}
          setPlantId={setPlantId}
          plants={plants}
          collapsed={sidebarCollapsed}
          setCollapsed={setSidebarCollapsed}
          mobileOpen={mobileSidebarOpen}
          setMobileOpen={setMobileSidebarOpen}
          optData={optData}
        />

        {/* Right Main Body */}
        <div
          className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
            sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-72'
          }`}
        >
          {/* Top Bar Header */}
          <TopBar
            activeTab={activeTab}
            plantInfo={currentPlant}
            onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
          />

          {/* Tab Content Container */}
          <main className="flex-1 w-full max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6">
            {activeTab === 'overview' && (
              <OverviewView
                data={overviewData}
                plantInfo={currentPlant}
                granularity={granularity}
                setGranularity={setGranularity}
                loading={loadingOverview}
              />
            )}

            {activeTab === 'forecast' && (
              <ForecastView data={forecastData} loading={loadingForecast} />
            )}

            {activeTab === 'battery' && (
              <BatteryScheduleView
                optData={optData}
                params={params}
                setParams={setParams}
                onRunOptimization={runOptimization}
                loading={loadingOpt}
              />
            )}

            {activeTab === 'savings' && (
              <TariffSavingsView optData={optData} params={params} />
            )}

            {activeTab === 'data' && <DataExplorerView plantId={plantId} />}
          </main>

          {/* Footer */}
          <footer className="mt-auto py-5 px-4 sm:px-8 bg-white/70 backdrop-blur-md border-t border-slate-200/60 text-xs text-slate-500">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-700">HeliosGrid Solar & BESS</span>
                <span>•</span>
                <span>PuLP Linear Programming Energy Arbitrage</span>
              </div>
              <div className="text-[11px] text-slate-400">
                Week 3 Production MVP • 24-Hour Solar Forecasting with Battery Storage
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
