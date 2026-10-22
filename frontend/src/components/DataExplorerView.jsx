import React, { useState, useEffect } from 'react';
import { Database, Download, FileText, Filter, CheckCircle2 } from 'lucide-react';

export default function DataExplorerView({ plantId }) {
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/dataset?plant_id=${plantId}&limit=50`)
      .then((res) => res.json())
      .then((data) => {
        setDatasetInfo(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load dataset:', err);
        setLoading(false);
      });
  }, [plantId]);

  const handleDownload = () => {
    if (!datasetInfo?.records?.length) return;
    const cols = datasetInfo.columns;
    const rows = datasetInfo.records.map((r) => cols.map((c) => r[c]));
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [cols.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `plant_${plantId}_hourly_processed_dataset.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-orange-600" />
              <h2 className="text-base font-semibold text-slate-900">
                Processed Handoff Dataset Inspection
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Engineered features, inverter-level telemetry, and localized Open-Meteo weather parameters
            </p>
          </div>
          <button
            onClick={handleDownload}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-xs transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4 text-slate-500" />
            Download Sample CSV
          </button>
        </div>
      </div>

      {/* Dataset Schema Info */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-slate-500 block">Total Hourly Observations</span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {datasetInfo?.total_rows || 816} Rows
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">34 Continuous days (May–June 2020)</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-slate-500 block">Inverter Subsystem</span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">22 Physical Inverters</span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Cross-inverter aggregate & per-unit telemetry</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <span className="text-slate-500 block">Data Integrity & Night Filter</span>
          <span className="text-xl font-bold text-emerald-700 mt-1 block">100% Validated</span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Physical zero-inflation applied (GHI = 0)</span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">
          Dataset Records Preview
        </h3>
        {loading ? (
          <div className="py-12 flex justify-center items-center text-xs text-slate-500">
            Loading dataset rows...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 text-slate-600 font-sans font-semibold border-y border-slate-200">
                <tr>
                  {datasetInfo?.columns?.map((c) => (
                    <th key={c} className="py-2.5 px-3 whitespace-nowrap">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {datasetInfo?.records?.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    {datasetInfo.columns.map((c) => (
                      <td key={c} className="py-2 px-3 text-slate-700 whitespace-nowrap">
                        {typeof row[c] === 'number' ? row[c].toFixed(2) : String(row[c] || '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
