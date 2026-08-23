import React, { useState } from 'react';
import { 
  Trash2, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ShieldAlert, 
  Cpu, 
  Database, 
  HardDrive,
  RefreshCw
} from 'lucide-react';

export default function SystemCleanup() {
  const [purging, setPurging] = useState(false);
  const [result, setResult] = useState(null);

  const handleRunPurge = async () => {
    setPurging(true);
    setResult(null);
    try {
      const res = await fetch('/api/cleanup/purge', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Purge failed");
      setResult(data);
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setPurging(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-rose-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            🧹 1-Click Cluster Purge & Memory Garbage Collection
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Reclaim cluster RAM, terminate abandoned Livy sessions, drop idle PostgreSQL metastore handles, leave HDFS safemode, and purge temporary scratch disks.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: PURGE ACTION CARD */}
        <div className="lg:col-span-5 glass-card p-6 space-y-5">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Safe Cluster Garbage Collection</h3>
              <p className="text-xs text-slate-400">Does not drop databases or destroy persistent tables.</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 space-y-2 text-xs text-slate-300">
            <div className="font-bold text-white mb-1">Items Automatically Purged:</div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">✓</span>
              <span>Abandoned Livy interactive session contexts</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">✓</span>
              <span>Idle PostgreSQL connections older than 2 minutes</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">✓</span>
              <span>HDFS SafeMode lock release & self-heal</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">✓</span>
              <span>Spark block manager scratch files in <code>/tmp</code></span>
            </div>
          </div>

          <button
            onClick={handleRunPurge}
            disabled={purging}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-lg shadow-rose-500/20"
          >
            {purging ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            Execute 1-Click Cluster Purge
          </button>
        </div>

        {/* RIGHT COLUMN: EXECUTION LOGS & REPORT */}
        <div className="lg:col-span-7 glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-rose-400" />
              Purge Execution Report
            </h3>
          </div>

          {!result && !purging && (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
              Click the button on the left to trigger full cluster garbage collection.
            </div>
          )}

          {purging && (
            <div className="p-8 text-center text-xs text-rose-400 bg-slate-950/60 rounded-xl border border-white/5 flex flex-col items-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>Scanning cluster sockets and terminating idle resources...</span>
            </div>
          )}

          {result && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Cluster Purge Completed</span>
              </div>

              <div className="space-y-1.5 font-mono text-xs text-slate-300">
                {result.logs?.map((log, idx) => (
                  <div key={idx} className="p-2 rounded bg-slate-900/60 border border-white/5">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
