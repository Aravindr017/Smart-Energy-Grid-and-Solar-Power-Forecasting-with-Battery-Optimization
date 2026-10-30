import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OverviewView from './components/OverviewView';
import ForecastView from './components/ForecastView';
import BatteryScheduleView from './components/BatteryScheduleView';
import TariffSavingsView from './components/TariffSavingsView';
import DataExplorerView from './components/DataExplorerView';
import WeatherStressView from './components/WeatherStressView';
import CarbonAccountingView from './components/CarbonAccountingView';
import ExecutiveReportView from './components/ExecutiveReportView';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [plantId, setPlantId] = useState(1);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(
    () => window.localStorage.getItem('solaris-theme') === 'dark',
  );

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

  const [granularity, setGranularity] = useState('15min_plant');
  const [overviewData, setOverviewData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [optData, setOptData] = useState(null);

  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(true);
  const [loadingOpt, setLoadingOpt] = useState(true);
  const [overviewError, setOverviewError] = useState(null);
  const [optError, setOptError] = useState(null);
  const [tariffConfigReady, setTariffConfigReady] = useState(false);

  const [params, setParams] = useState({
    plant_id: 1,
    battery_capacity_mwh: 10.0,
    max_inverter_power_mw: 5.0,
    round_trip_efficiency_pct: 90.25,
    initial_soc_pct: 20.0,
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkTheme);
    window.localStorage.setItem('solaris-theme', isDarkTheme ? 'dark' : 'light');
  }, [isDarkTheme]);

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

  useEffect(() => {
    setParams((prev) => ({ ...prev, plant_id: plantId }));
  }, [plantId]);

  useEffect(() => {
    let active = true;
    fetch('/api/tariff-config')
      .then(async (res) => {
        const payload = await res.json().catch(() => null);
        if (!res.ok) {
          throw new Error(payload?.detail || `HTTP ${res.status}`);
        }
        if (!payload?.tariff_rates || !payload?.financial_assumptions) {
          throw new Error('The API did not return tariff defaults.');
        }
        return payload;
      })
      .then((config) => {
        if (!active) return;
        setParams((prev) => ({
          ...prev,
          ...config.tariff_rates,
          ...config.financial_assumptions,
        }));
        setTariffConfigReady(true);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load simulated INR tariff settings:', err);
        setOptError(err.message === 'Failed to fetch'
          ? 'Cannot reach the SOLARIS API to load INR tariff assumptions.'
          : err.message);
        setLoadingOpt(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const loadOverview = useCallback(() => {
    setLoadingOverview(true);
    setOverviewError(null);
    fetch(`/api/overview?plant_id=${plantId}&granularity=${granularity}&limit=72`)
      .then(async (res) => {
        const payload = await res.json().catch(() => null);
        if (!res.ok) {
          const detail = payload?.detail || `HTTP ${res.status}`;
          throw new Error(typeof detail === 'string' ? detail : 'Overview request failed');
        }
        if (!payload?.kpis || !Array.isArray(payload?.timeseries)) {
          throw new Error('The plant telemetry service did not return results for this selection.');
        }
        return payload;
      })
      .then((data) => {
        setOverviewData(data);
        setLoadingOverview(false);
      })
      .catch((err) => {
        console.error('Failed to load overview:', err);
        setOverviewData(null);
        setOverviewError(err.message === 'Failed to fetch'
          ? 'Cannot reach the SOLARIS API. Start the backend on port 8000, then refresh.'
          : err.message);
        setLoadingOverview(false);
      });
  }, [plantId, granularity]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const loadForecast = useCallback(() => {
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
  }, [plantId]);

  useEffect(() => {
    loadForecast();
  }, [loadForecast]);

  const runOptimization = useCallback(() => {
    if (!tariffConfigReady) return;
    setLoadingOpt(true);
    setOptError(null);
    fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => null);
        if (!res.ok) {
          const detail = payload?.detail || `HTTP ${res.status}`;
          throw new Error(typeof detail === 'string' ? detail : 'Optimization request failed');
        }
        if (!payload?.kpis || !Array.isArray(payload?.schedule) || !payload?.financials) {
          throw new Error('The optimization service returned an incomplete result.');
        }
        return payload;
      })
      .then((data) => {
        setOptData(data);
        setLoadingOpt(false);
      })
      .catch((err) => {
        console.error('Failed to run optimization:', err);
        setOptData(null);
        setOptError(err.message === 'Failed to fetch'
          ? 'Cannot reach the SOLARIS API. Start the backend on port 8000, then try again.'
          : err.message);
        setLoadingOpt(false);
      });
  }, [params, tariffConfigReady]);

  useEffect(() => {
    if (tariffConfigReady) runOptimization();
  }, [runOptimization, tariffConfigReady]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadOverview();
    loadForecast();
    runOptimization();
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const currentPlant = plants.find((p) => p.id === plantId) || plants[0];

  return (
    <div className="relative min-h-screen bg-slate-50 text-slate-800 font-sans antialiased overflow-x-hidden">
      <div className="relative z-10 flex min-h-screen">
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
        />

        <div
          className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
            sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-72'
          }`}
        >
          <TopBar
            activeTab={activeTab}
            plantInfo={currentPlant}
            onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
            isDarkTheme={isDarkTheme}
            onToggleTheme={() => setIsDarkTheme((current) => !current)}
          />

          <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {activeTab === 'overview' && (
              <OverviewView
                data={overviewData}
                plantInfo={currentPlant}
                granularity={granularity}
                setGranularity={setGranularity}
                loading={loadingOverview}
                error={overviewError}
                onRetry={loadOverview}
                forecastData={forecastData}
                optData={optData}
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
              <TariffSavingsView
                optData={optData}
                params={params}
                setParams={setParams}
                onRunOptimization={runOptimization}
                loading={loadingOpt}
                error={optError}
              />
            )}

            {activeTab === 'data' && <DataExplorerView plantId={plantId} />}

            {activeTab === 'weather' && <WeatherStressView plantId={plantId} />}

            {activeTab === 'carbon' && <CarbonAccountingView plantId={plantId} />}

            {activeTab === 'report' && <ExecutiveReportView plantId={plantId} />}
          </main>

          <footer className="mt-auto py-4 px-4 sm:px-8 border-t border-slate-200 bg-white text-xs text-slate-500">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <span className="font-medium text-slate-700">SOLARIS Energy Platform</span>
              <span>Solar forecasting, battery optimization, weather stress, and carbon estimates</span>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
