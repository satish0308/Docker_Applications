import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  Plus, 
  Play, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Power, 
  FolderSearch, 
  RefreshCw, 
  Database,
  Calendar,
  Layers,
  Sparkles
} from 'lucide-react';

export default function ScheduledJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Form State
  const [name, setName] = useState('hourly_sales_ingest');
  const [watchPath, setWatchPath] = useState('hdfs://namenode:9000/data/incoming/*.csv');
  const [targetDb, setTargetDb] = useState('default');
  const [targetTable, setTargetTable] = useState('sales_stream');
  const [format, setFormat] = useState('delta');
  const [interval, setInterval] = useState('Hourly');
  const [creating, setCreating] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/schedule/jobs');
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch('/api/schedule/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          watch_path: watchPath,
          target_database: targetDb,
          target_table: targetTable,
          format,
          interval
        })
      });
      if (!res.ok) throw new Error("Failed to create scheduled job");
      fetchJobs();
      setName('');
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (jobId) => {
    try {
      await fetch(`/api/schedule/toggle/${jobId}`, { method: 'POST' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (jobId) => {
    try {
      await fetch(`/api/schedule/${jobId}`, { method: 'DELETE' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunNow = async (jobId) => {
    try {
      await fetch(`/api/schedule/run-now/${jobId}`, { method: 'POST' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-amber-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            ⏰ Scheduled Batch Ingestion & Directory Watchers
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Automate recurring batch pipelines to monitor HDFS / S3 directories and automatically append delta updates into Hive tables on a schedule.
          </p>
        </div>
        <button
          onClick={fetchJobs}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-amber-400 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: CREATE PIPELINE */}
        <div className="lg:col-span-5 glass-card p-6 space-y-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
            <Plus className="w-4 h-4 text-amber-400" />
            1. Create Scheduled Ingestion Pipeline
          </h3>

          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Pipeline Name</label>
              <input
                type="text"
                required
                placeholder="e.g. hourly_sales_ingest"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Watch Folder / HDFS Wildcard</label>
              <input
                type="text"
                required
                value={watchPath}
                onChange={(e) => setWatchPath(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Database</label>
                <input
                  type="text"
                  value={targetDb}
                  onChange={(e) => setTargetDb(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Table</label>
                <input
                  type="text"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-bold text-white focus:outline-none focus:border-amber-500"
                >
                  <option value="delta">Delta Lake</option>
                  <option value="parquet">Apache Parquet</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Execution Interval</label>
                <select
                  value={interval}
                  onChange={(e) => setInterval(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-bold text-white focus:outline-none focus:border-amber-500"
                >
                  <option value="Every 15 Minutes">Every 15 Minutes</option>
                  <option value="Hourly">Hourly</option>
                  <option value="Daily at Midnight">Daily at Midnight</option>
                  <option value="Manual / On-Demand">Manual / On-Demand</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={creating || !name}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-lg shadow-amber-500/20"
            >
              <Plus className="w-4 h-4" />
              Save Ingestion Pipeline
            </button>
          </form>
        </div>

        {/* RIGHT COLUMN: CONFIGURED PIPELINES LIST */}
        <div className="lg:col-span-7 glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              Active Ingestion Pipelines ({jobs.length})
            </h3>
          </div>

          {jobs.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
              No scheduled pipelines created yet. Use the form on the left to configure automated batch watchers.
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto custom-scrollbar">
              {jobs.map((j) => {
                const isEnabled = j.enabled !== false;
                return (
                  <div
                    key={j.job_id}
                    className={`p-4 rounded-xl border transition space-y-3 ${
                      isEnabled 
                        ? 'bg-slate-900/70 border-white/10 hover:border-amber-500/30' 
                        : 'bg-slate-950/40 border-white/5 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className={`w-2 h-2 rounded-full ${isEnabled ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-slate-600'}`} />
                        <span className="font-extrabold text-sm text-white">{j.name}</span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-amber-300 border border-amber-500/20">
                          {j.interval}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleRunNow(j.job_id)}
                          className="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-bold flex items-center gap-1 transition"
                          title="Trigger Now"
                        >
                          <Play className="w-3 h-3 fill-current" />
                          Run
                        </button>
                        <button
                          onClick={() => handleToggle(j.job_id)}
                          className={`p-1.5 rounded-lg border transition ${
                            isEnabled 
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20' 
                              : 'bg-slate-800 border-white/10 text-slate-400 hover:text-white'
                          }`}
                          title={isEnabled ? "Pause Pipeline" : "Activate Pipeline"}
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(j.job_id)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/40 border border-white/10 text-slate-400 hover:text-rose-400 transition"
                          title="Delete Pipeline"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="text-xs font-mono text-slate-400 space-y-1 bg-slate-950/80 p-2.5 rounded-lg border border-white/5">
                      <div><span className="text-slate-500">Watch:</span> <span className="text-slate-300">{j.watch_path}</span></div>
                      <div><span className="text-slate-500">Target:</span> <span className="text-sky-300">{j.target_database}.{j.target_table} ({j.format})</span></div>
                      <div className="text-[10px] text-slate-500 pt-1 flex items-center justify-between border-t border-white/5">
                        <span>Last Run: {j.last_run || 'Never'}</span>
                        <span>Created: {j.created_at}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
