import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Terminal, 
  Database, 
  Trash2, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Sparkles,
  Copy,
  Table as TableIcon
} from 'lucide-react';

export default function SqlStudio() {
  const [sql, setSql] = useState(`CREATE TABLE IF NOT EXISTS inventory_delta
USING DELTA
PARTITIONED BY (season)
AS SELECT 
    inv_item_sk,
    inv_quantity_on_hand,
    'Q3_PEAK' AS season
FROM delta_bronze_events
LIMIT 1000;`);

  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchJobs = async () => {
    try {
      const res = await fetch('/api/sql/jobs');
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error("Failed to load SQL jobs", err);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleExecute = async () => {
    if (!sql.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql })
      });
      const data = await res.json();
      fetchJobs();
    } catch (ex) {
      alert(`Submission error: ${ex}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteJob = async (queryId) => {
    try {
      await fetch(`/api/sql/jobs/${queryId}`, { method: 'DELETE' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const templates = [
    {
      title: "Broadcast Hash Join (Fastest)",
      query: `SELECT /*+ BROADCAST(d) */ 
    e.event_id, e.user_id, d.store_name, e.amount
FROM sales_events e
JOIN store_dim d ON e.store_id = d.store_id
LIMIT 500;`
    },
    {
      title: "Delta Vacuum Retention (7 Days)",
      query: `VACUUM inventory_delta RETAIN 168 HOURS;`
    },
    {
      title: "Hive Metastore Catalog Inspector",
      query: `SHOW TABLES IN default;`
    }
  ];

  const runningJobs = jobs.filter(j => j.status === 'RUNNING');
  const completedJobs = jobs.filter(j => j.status !== 'RUNNING');

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="glass-card p-6 border-l-4 border-l-sky-500">
        <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
          ⚡ Persistent Spark SQL Studio & Live DAG Tracer
        </h2>
        <p className="text-xs text-slate-300 mt-1 max-w-3xl">
          Execute heavy analytical queries asynchronously across the distributed Spark cluster. Queries run decoupled in the background and <b>survive browser hard-refreshes (<code>Ctrl+F5</code>), tab closures, and network drops</b>.
        </p>
      </div>

      {/* IN-FLIGHT RUNNING JOBS */}
      {runningJobs.length > 0 && (
        <div className="glass-card p-5 space-y-3 border border-sky-500/40">
          <div className="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
            </span>
            Active Queries Running in Spark Cluster ({runningJobs.length})
          </div>

          <div className="space-y-3">
            {runningJobs.map(job => (
              <div key={job.query_id} className="p-4 rounded-xl bg-slate-900/90 border border-sky-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                <div>
                  <div className="font-mono text-xs font-bold text-sky-300 flex items-center gap-2">
                    <span>Query ID: {job.query_id}</span>
                    <span className="px-2 py-0.5 rounded bg-sky-500/20 text-[10px] text-sky-300 border border-sky-500/30">RUNNING</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Submitted at: {job.submitted_at}</div>
                </div>
                <div className="font-mono text-[11px] text-slate-400 max-w-md line-clamp-1 bg-slate-950 px-3 py-1.5 rounded-lg border border-white/5">
                  {job.recent_logs}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SQL EDITOR */}
      <div className="glass-card p-6 space-y-4">
        
        {/* Templates Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <span className="text-xs font-bold text-slate-400 flex-shrink-0">⚡ Quick Templates:</span>
          {templates.map((t, idx) => (
            <button
              key={idx}
              onClick={() => setSql(t.query)}
              className="px-3 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-xs font-medium text-slate-300 flex-shrink-0 transition"
            >
              {t.title}
            </button>
          ))}
        </div>

        {/* Code Area */}
        <div className="relative">
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            rows={8}
            className="w-full bg-[#05070c] border border-white/15 rounded-xl p-4 font-mono text-xs text-sky-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition custom-scrollbar"
            placeholder="Write standard ANSI SQL or SparkSQL here..."
          />
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-slate-500 font-mono">
            Directly binds to Spark Master (Port 7077) & Hive Metastore (Port 9083)
          </div>
          <button
            onClick={handleExecute}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-sky-600 to-emerald-600 hover:opacity-90 text-white font-bold text-xs shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {loading ? 'Submitting to Spark...' : '⚡ Execute Asynchronous Query'}
          </button>
        </div>
      </div>

      {/* QUERY EXECUTION HISTORY */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
          📜 Query Execution Audit & History
        </h3>

        {completedJobs.length === 0 ? (
          <div className="text-xs text-slate-500 py-6 text-center">No completed queries in registry yet.</div>
        ) : (
          <div className="space-y-3">
            {completedJobs.map(job => {
              const isSuccess = job.status === 'SUCCESS';
              return (
                <div key={job.query_id} className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.08] space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                        isSuccess 
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                          : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                      }`}>
                        {job.status}
                      </span>
                      <span className="font-mono text-xs text-white font-bold">{job.query_id}</span>
                      <span className="text-xs text-slate-400">• Completed at {job.completed_at}</span>
                    </div>

                    <button
                      onClick={() => handleDeleteJob(job.query_id)}
                      className="text-slate-500 hover:text-rose-400 transition"
                      title="Delete Record"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-white/5 font-mono text-xs text-slate-300 overflow-x-auto">
                    <code>{job.query_sql}</code>
                  </div>

                  {job.result_preview && (
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-emerald-500/20 font-mono text-[11px] text-emerald-300 max-h-40 overflow-y-auto custom-scrollbar whitespace-pre-wrap">
                      {job.result_preview}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
