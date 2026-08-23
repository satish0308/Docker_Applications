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
  RefreshCw,
  RotateCcw,
  Zap,
  Server
} from 'lucide-react';

export default function SystemCleanup() {
  const [purging, setPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState(null);

  // Clean run state
  const [cleanRunning, setCleanRunning] = useState(false);
  const [cleanRunResult, setCleanRunResult] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const handleRunPurge = async () => {
    setPurging(true);
    setPurgeResult(null);
    try {
      const res = await fetch('/api/cleanup/purge', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Purge failed");
      setPurgeResult(data);
    } catch (err) {
      setPurgeResult({ error: err.message });
    } finally {
      setPurging(false);
    }
  };

  const handleExecuteCleanRun = async () => {
    setShowConfirmModal(false);
    setCleanRunning(true);
    setCleanRunResult(null);
    try {
      const res = await fetch('/api/cleanup/clean-run', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Clean run failed");
      setCleanRunResult(data);
    } catch (err) {
      setCleanRunResult({ error: err.message });
    } finally {
      setCleanRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-rose-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            🧹 1-Click Cluster Maintenance, Purge & Clean Run
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Safely reclaim cluster RAM, purge idle database connections and scratch disks, or execute a total nuclear clean recreation of all platform pods.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* OPTION 1: SAFE GARBAGE COLLECTION */}
        <div className="lg:col-span-6 glass-card p-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Safe Cluster Garbage Collection</h3>
                <p className="text-xs text-slate-400">Non-destructive memory reclaim without stopping pods.</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 space-y-2 text-xs text-slate-300">
              <div className="font-bold text-white mb-1">Garbage Collection Actions:</div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-400">✓</span>
                <span>Terminates abandoned Livy interactive session contexts</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-400">✓</span>
                <span>Drops idle PostgreSQL connections older than 2 minutes</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-400">✓</span>
                <span>HDFS SafeMode lock release & self-heal</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-400">✓</span>
                <span>Purges Spark block manager temporary files in <code>/tmp</code></span>
              </div>
            </div>
          </div>

          <button
            onClick={handleRunPurge}
            disabled={purging || cleanRunning}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-lg shadow-amber-500/20"
          >
            {purging ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            Execute Safe Garbage Collection
          </button>
        </div>

        {/* OPTION 2: NUCLEAR CLEAN RUN / FACTORY RECREATE */}
        <div className="lg:col-span-6 glass-card p-6 space-y-5 flex flex-col justify-between border-2 border-rose-500/30 bg-rose-950/10">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-rose-500/20 border border-rose-500/40 text-rose-400">
                <ShieldAlert className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <h3 className="text-sm font-black text-rose-300 flex items-center gap-2">
                  ⚡ Nuclear Option: Complete Clean Run
                </h3>
                <p className="text-xs text-slate-400">Last resort to repair corrupted states & restart clean.</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-rose-500/20 space-y-2 text-xs text-slate-300">
              <div className="font-bold text-rose-300 mb-1">Clean Run Sequence:</div>
              <div className="flex items-center gap-2">
                <span className="text-rose-400 font-bold">1.</span>
                <span>Forcefully stops & removes all cluster containers</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rose-400 font-bold">2.</span>
                <span>Recreates fresh containers in topological dependency order</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rose-400 font-bold">3.</span>
                <span>Re-initializes PostgreSQL metastore & grants (<code>hueuser</code>, <code>keycloak</code>)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rose-400 font-bold">4.</span>
                <span>Provisions seed Delta Lake tables (<code>default.sales</code>, <code>default.inventory_delta</code>)</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowConfirmModal(true)}
            disabled={purging || cleanRunning}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-600 via-red-600 to-rose-700 hover:opacity-90 text-white font-black text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-xl shadow-rose-500/30"
          >
            {cleanRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            ⚡ Recreate All Containers (Clean Run)
          </button>
        </div>

      </div>

      {/* EXECUTION LOGS & AUDIT REPORT */}
      {(purgeResult || cleanRunResult || purging || cleanRunning) && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-sky-400" />
              Maintenance & Recreation Execution Console
            </h3>
          </div>

          {purging && (
            <div className="p-8 text-center text-xs text-amber-300 bg-slate-950/60 rounded-xl border border-white/5 flex flex-col items-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>Scanning cluster sockets and terminating idle connections...</span>
            </div>
          )}

          {cleanRunning && (
            <div className="p-8 text-center text-xs text-rose-300 bg-slate-950/60 rounded-xl border border-white/5 flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-rose-400" />
              <span className="font-bold">Executing Nuclear Clean Run: Removing pods, creating fresh containers, and seeding Metastore...</span>
              <span className="text-[11px] text-slate-400">This may take ~15-20 seconds. Please do not close your browser.</span>
            </div>
          )}

          {purgeResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Safe Garbage Collection Complete</span>
              </div>
              <div className="space-y-1 font-mono text-xs text-slate-300">
                {purgeResult.logs?.map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
              </div>
            </div>
          )}

          {cleanRunResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-rose-500/30 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Nuclear Clean Run Completed Successfully</span>
              </div>
              <div className="space-y-1 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto custom-scrollbar">
                {cleanRunResult.logs?.map((l, i) => (
                  <div key={i} className="py-0.5">{l}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* CONFIRMATION MODAL */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="glass-card max-w-md w-full p-6 space-y-5 border-2 border-rose-500/50 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <ShieldAlert className="w-8 h-8 flex-shrink-0" />
              <div>
                <h3 className="text-base font-black text-white">Confirm Total Clean Run?</h3>
                <p className="text-xs text-slate-400">Action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              This will <b>forcefully terminate and remove all cluster containers</b>, recreate them from scratch, re-initialize PostgreSQL permissions and seed default Delta Lake tables.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteCleanRun}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-bold text-white transition shadow-lg shadow-rose-600/30"
              >
                Yes, Recreate All Containers
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
