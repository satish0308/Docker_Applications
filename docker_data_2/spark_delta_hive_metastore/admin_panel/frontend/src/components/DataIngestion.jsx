import React, { useState, useEffect } from 'react';
import { 
  UploadCloud, 
  FileSpreadsheet, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Database, 
  Layers, 
  HardDrive, 
  Clock,
  RefreshCw,
  Eye,
  Sliders
} from 'lucide-react';

export default function DataIngestion() {
  const [file, setFile] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [schemaPreview, setSchemaPreview] = useState(null);

  // Ingestion config
  const [targetDb, setTargetDb] = useState('default');
  const [targetTable, setTargetTable] = useState('sales_data');
  const [format, setFormat] = useState('delta');
  const [writeMode, setWriteMode] = useState('append');
  const [partitionCols, setPartitionCols] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(false);

  const fetchJobs = async () => {
    setJobsLoading(true);
    try {
      const res = await fetch('/api/ingestion/jobs');
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setFile(selectedFile);
    setPreviewLoading(true);
    setSchemaPreview(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch('/api/ingestion/preview-schema', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to preview schema");
      setSchemaPreview(data);
      
      // Auto-populate table name from filename
      const baseName = selectedFile.name.split('.')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_');
      setTargetTable(baseName);
    } catch (err) {
      console.error("Schema preview error:", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setSubmitting(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_database', targetDb);
    formData.append('target_table', targetTable);
    formData.append('table_format', format);
    formData.append('write_mode', writeMode);
    formData.append('partition_cols', partitionCols);

    try {
      const res = await fetch('/api/ingestion/submit', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Submission failed");
      fetchJobs();
    } catch (err) {
      console.error("Ingestion submit error:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-sky-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            📥 Micro-Batch Data Ingestion & Partitioning Studio
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Upload CSV/Parquet files to auto-detect schema, specify multidimensional partition columns, configure Spark compute sizing, and write datasets directly into <b>Delta Lake / Hive Metastore</b>.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: UPLOAD & CONFIGURATION */}
        <div className="lg:col-span-6 space-y-6">
          
          <div className="glass-card p-6 space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400 flex items-center gap-2">
              <UploadCloud className="w-4 h-4 text-sky-400" />
              1. Upload Source File
            </h3>

            <label className="border-2 border-dashed border-white/15 hover:border-sky-500/50 rounded-2xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition bg-slate-950/40 hover:bg-slate-900/60">
              <FileSpreadsheet className="w-8 h-8 text-sky-400" />
              <div className="text-center">
                <span className="text-xs font-bold text-white">Click or drag CSV / Parquet file</span>
                <p className="text-[11px] text-slate-400 mt-0.5">Supports automated chunking & parallel Spark writes</p>
              </div>
              <input type="file" accept=".csv,.parquet,.pq" onChange={handleFileChange} className="hidden" />
            </label>

            {previewLoading && (
              <div className="flex items-center gap-2 text-xs text-sky-400 font-semibold justify-center py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Inferring file schema & sample data...
              </div>
            )}
          </div>

          {/* Target Storage & Partitioning Config */}
          <div className="glass-card p-6 space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-400" />
              2. Target Table & Partition Settings
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Database</label>
                <input
                  type="text"
                  value={targetDb}
                  onChange={(e) => setTargetDb(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Table Name</label>
                <input
                  type="text"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Storage Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-bold text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="delta">Delta Lake (ACID + Time-Travel)</option>
                  <option value="parquet">Apache Parquet</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Write Mode</label>
                <select
                  value={writeMode}
                  onChange={(e) => setWriteMode(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-bold text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="append">Append (Add to existing)</option>
                  <option value="overwrite">Overwrite (Replace table)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Partition Columns (Optional, comma-separated e.g. <code>year, country</code>)
              </label>
              <input
                type="text"
                placeholder="e.g. region, store_id"
                value={partitionCols}
                onChange={(e) => setPartitionCols(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting || !file}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-lg shadow-indigo-500/20"
            >
              {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
              Launch Ingestion Job into Delta Lake
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: SCHEMA PREVIEW & IN-FLIGHT JOBS */}
        <div className="lg:col-span-6 space-y-6">
          
          {/* SCHEMA PREVIEW */}
          {schemaPreview && (
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                  <Eye className="w-4 h-4 text-emerald-400" />
                  Detected Schema Preview ({schemaPreview.columns?.length} Columns)
                </h3>
                <span className="text-xs font-mono text-slate-400">{schemaPreview.rows_count} Rows Sampled</span>
              </div>

              <div className="max-h-60 overflow-y-auto border border-white/10 rounded-xl bg-slate-950/80 custom-scrollbar">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900 border-b border-white/10 text-slate-400">
                    <tr>
                      <th className="p-2.5">Column</th>
                      <th className="p-2.5">Suggested Type</th>
                      <th className="p-2.5">Sample Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300">
                    {schemaPreview.schema?.map((col) => (
                      <tr key={col.column} className="hover:bg-white/[0.02]">
                        <td className="p-2.5 font-bold text-white">{col.column}</td>
                        <td className="p-2.5 text-sky-400">{col.suggested_sql_type}</td>
                        <td className="p-2.5 text-slate-400 truncate max-w-[120px]">{col.sample}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* IN-FLIGHT & HISTORICAL JOBS */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-sky-400" />
                Ingestion Job Tracker ({jobs.length})
              </h3>
              <button onClick={fetchJobs} className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400">
                <RefreshCw className={`w-3 h-3 ${jobsLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {jobs.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
                No ingestion jobs active. Upload a dataset to begin.
              </div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
                {jobs.map((j) => {
                  const isDone = j.status === "COMPLETED";
                  const isFail = j.status === "FAILED";
                  const isRun = j.status === "RUNNING" || j.status === "QUEUED";

                  return (
                    <div key={j.job_id} className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="font-extrabold text-xs text-white flex items-center gap-2">
                          <span>{j.target_database}.{j.target_table}</span>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400">
                            {j.format}
                          </span>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border flex items-center gap-1 ${
                          isDone 
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                            : isFail 
                            ? 'bg-rose-500/10 border-rose-500/30 text-rose-400' 
                            : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                        }`}>
                          {isRun && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                          {isDone && <CheckCircle2 className="w-2.5 h-2.5" />}
                          {isFail && <AlertCircle className="w-2.5 h-2.5" />}
                          {j.status}
                        </span>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={`h-1.5 transition-all duration-300 ${isDone ? 'bg-emerald-400' : isFail ? 'bg-rose-500' : 'bg-indigo-500'}`}
                          style={{ width: `${j.progress_pct || 10}%` }}
                        />
                      </div>

                      <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between">
                        <span>{j.current_batch_msg || 'Processing...'}</span>
                        <span>{j.created_at}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
