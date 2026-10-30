import React, { useState } from 'react';
import { Download, RefreshCw, CheckCircle2, AlertTriangle, FileText } from 'lucide-react';
import PageHeader from './ui/PageHeader';
import PrimaryButton from './ui/PrimaryButton';
import SecondaryButton from './ui/SecondaryButton';
import LoadingState from './ui/LoadingState';
import StatusBadge from './ui/StatusBadge';

export default function ExecutiveReportView({ plantId = 1 }) {
  const [generating, setGenerating] = useState(false);
  const [reportMeta, setReportMeta] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const sections = [
    { num: '1', title: 'Executive summary', desc: 'Plant KPIs and disclosures, including the illustrative demand profile and assumed tariffs.' },
    { num: '2', title: 'Solar generation', desc: 'Diurnal power, irradiance, and temperature context.' },
    { num: '3', title: 'Forecasting', desc: 'Model comparison and uncertainty bounds from the existing forecast run.' },
    { num: '4', title: 'Duck curve', desc: 'Demand profile, net load, and evening ramp.' },
    { num: '5', title: 'Battery optimization', desc: 'Dispatch, state of charge, and estimated savings based on simulated INR tariff assumptions.' },
    { num: '6', title: 'Weather and carbon', desc: 'Stress scenarios and estimated avoided emissions.' },
  ];

  const handleGenerate = () => {
    setGenerating(true);
    setError(null);
    setSuccessMsg(null);

    fetch(`/api/executive-report/generate?plant_id=${plantId}`, { method: 'POST' })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to generate executive report`);
        return res.json();
      })
      .then((json) => {
        setReportMeta(json);
        setSuccessMsg(`Report generated (${json.size_kb} KB)`);
        setGenerating(false);
      })
      .catch((err) => {
        console.error('Report generation error:', err);
        setError(err.message);
        setGenerating(false);
      });
  };

  const handleDownload = () => {
    window.open(`/api/executive-report/download?plant_id=${plantId}`, '_blank');
  };

  return (
    <div className="page-stack">
      <PageHeader
        title="Executive report"
        description="Generate a PDF from the current plant analysis. The file is built by the existing report service; this page only starts the job and downloads the result."
        actions={
          <div className="flex flex-wrap gap-2">
            <SecondaryButton onClick={handleGenerate} disabled={generating}>
              <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
              {generating ? 'Generating…' : 'Generate report'}
            </SecondaryButton>
            <PrimaryButton onClick={handleDownload} disabled={generating}>
              <Download className="w-4 h-4" />
              Download PDF
            </PrimaryButton>
          </div>
        }
      />

      <div className="surface-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <p className="muted-label">Reporting plant</p>
          <p className="mt-1 text-lg font-semibold text-slate-900">Plant {plantId}</p>
          <p className="text-xs text-slate-500 mt-1">Change the plant in the sidebar, then generate again.</p>
        </div>
        <StatusBadge tone={reportMeta ? 'success' : 'slate'}>
          {reportMeta ? `Ready · ${reportMeta.size_kb} KB` : 'Not generated this session'}
        </StatusBadge>
      </div>

      {generating && <LoadingState label="Compiling the PDF from current results…" />}

      {successMsg && (
        <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <CheckCircle2 className="w-4 h-4" />
          {successMsg}
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sections.map((sec) => (
            <article key={sec.num} className="surface-card p-4">
              <p className="muted-label">Page {sec.num}</p>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">{sec.title}</h3>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">{sec.desc}</p>
            </article>
          ))}
        </div>

        <aside className="surface-card p-5 space-y-3 text-sm">
          <div className="flex items-center gap-2 font-semibold text-slate-900">
            <FileText className="w-4 h-4 text-emerald-700" />
            What you get
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Plant</span>
            <span className="font-medium text-slate-900">{plantId}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Pages</span>
            <span className="font-medium text-slate-900">6</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Status</span>
            <span className="font-medium text-slate-900">{reportMeta ? 'Generated' : 'Waiting'}</span>
          </div>
          <PrimaryButton className="w-full mt-2" onClick={handleDownload}>
            <Download className="w-4 h-4" />
            Download PDF
          </PrimaryButton>
          <p className="text-xs text-slate-500">
            The download endpoint is unchanged. Generate first if you need a freshly compiled file.
          </p>
        </aside>
      </div>
    </div>
  );
}
