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
  Table as TableIcon,
  ChevronDown,
  ChevronUp,
  Layers,
  Eraser
} from 'lucide-react';

export default function SqlStudio() {
  const [sql, setSql] = useState(`SHOW TABLES IN default;`);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const fetchJobs = async () => {
    try {
      const res = await fetch('/api/sql/jobs');
      const data = await res.json();
      const jobList = data.jobs || [];
      setJobs(jobList);
      
      // Auto-expand the most recent completed job if none is currently selected
      const completed = jobList.filter(j => j.status !== 'RUNNING');
      if (completed.length > 0) {
        setExpandedId(prev => (prev ? prev : completed[0].query_id));
      }
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
      if (data.query_id) {
        setExpandedId(data.query_id);
      }
      fetchJobs();
    } catch (ex) {
      alert(`Submission error: ${ex}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteJob = async (queryId, e) => {
    if (e) e.stopPropagation();
    try {
      await fetch(`/api/sql/jobs/${queryId}`, { method: 'DELETE' });
      if (expandedId === queryId) setExpandedId(null);
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleClearAllJobs = async () => {
    if (!window.confirm("Are you sure you want to clear all query execution history?")) return;
    try {
      await fetch('/api/sql/jobs/clear-all', { method: 'DELETE' });
      setExpandedId(null);
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleExpand = (queryId) => {
    setExpandedId(prev => (prev === queryId ? null : queryId));
  };

  const templates = [
    {
      title: "Show Tables (Hive Metastore)",
      query: `SHOW TABLES IN default;`
    },
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
      title: "Create Delta Table",
      query: `CREATE TABLE IF NOT EXISTS default.sales_demo
USING DELTA
AS SELECT 1 AS id, 'Retail' AS category, 250.00 AS amount;`
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
            rows={7}
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
            {loading ? 'Submitting to Spark...' : '⚡ Run Distributed Query'}
          </button>
        </div>
      </div>

      {/* QUERY EXECUTION HISTORY (MINIMIZED ACCORDION LIST) */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            Query Execution Audit & History ({completedJobs.length})
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClearAllJobs}
              disabled={completedJobs.length === 0}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-bold border border-white/10 flex items-center gap-1.5 transition disabled:opacity-40"
              title="Clear all query execution history"
            >
              <Eraser className="w-3.5 h-3.5 text-rose-400" />
              Clear History
            </button>
            <span className="text-[11px] text-slate-400 font-mono hidden md:inline">
              Latest query auto-expanded • click older queries to inspect
            </span>
          </div>
        </div>

        {completedJobs.length === 0 ? (
          <div className="text-xs text-slate-500 py-8 text-center bg-slate-950/40 rounded-xl border border-white/5">
            No completed queries in registry yet. Write SQL above and click Run Distributed Query.
          </div>
        ) : (
          <div className="space-y-2.5">
            {completedJobs.map((job, idx) => {
              const isSuccess = job.status === 'SUCCESS';
              const isExpanded = expandedId === job.query_id;
              const isLatest = idx === 0;

              return (
                <div 
                  key={job.query_id} 
                  className={`rounded-xl border transition overflow-hidden ${
                    isExpanded 
                      ? 'bg-slate-900/80 border-sky-500/40 shadow-lg shadow-sky-500/5' 
                      : 'bg-slate-900/40 border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  {/* Accordion Header / Summary Row */}
                  <div 
                    onClick={() => toggleExpand(job.query_id)}
                    className="p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* Status Badge */}
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border flex items-center gap-1 flex-shrink-0 ${
                        isSuccess 
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                          : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                      }`}>
                        {isSuccess ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                        {job.status}
                      </span>

                      {/* Query ID */}
                      <span className="font-mono text-xs text-white font-bold flex-shrink-0">
                        {job.query_id}
                      </span>

                      {isLatest && (
                        <span className="px-1.5 py-0.2 rounded bg-sky-500/20 text-[9px] font-bold text-sky-300 border border-sky-500/30 flex-shrink-0">
                          LATEST
                        </span>
                      )}

                      {/* Truncated SQL snippet in header */}
                      <span className="font-mono text-[11px] text-slate-400 truncate hidden sm:inline-block max-w-md">
                        {job.query_sql.replace(/\n/g, ' ')}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className="text-[11px] text-slate-500 font-mono hidden md:inline-block">
                        {job.completed_at || job.submitted_at}
                      </span>

                      <button
                        onClick={(e) => handleDeleteJob(job.query_id, e)}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 transition"
                        title="Delete Record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      <div className="text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-sky-400" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Body: SQL Code & Result Preview */}
                  {isExpanded && (
                    <div className="p-4 pt-0 space-y-3 border-t border-white/5 mt-1 bg-slate-950/60">
                      
                      {/* Full Query Code Box */}
                      <div className="space-y-1 pt-3">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Executed SQL</div>
                        <div className="p-3 rounded-lg bg-slate-950 border border-white/10 font-mono text-xs text-sky-300 overflow-x-auto">
                          <pre className="whitespace-pre-wrap">{job.query_sql}</pre>
                        </div>
                      </div>

                      {/* Result / Output Preview */}
                      <div className="space-y-1">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          {isSuccess ? 'Query Output Preview' : 'Execution Error Logs'}
                        </div>
                        <div className={`p-3.5 rounded-lg border font-mono text-xs max-h-56 overflow-y-auto custom-scrollbar whitespace-pre-wrap ${
                          isSuccess 
                            ? 'bg-slate-950/90 border-emerald-500/30 text-emerald-300' 
                            : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
                        }`}>
                          {job.result_preview || job.recent_logs || 'No output returned.'}
                        </div>
                      </div>

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
