import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  HardDrive, 
  Layers, 
  Zap, 
  Sliders, 
  CheckCircle2, 
  RefreshCw, 
  Server,
  Activity
} from 'lucide-react';

export default function SparkTuning({ onProfileChange }) {
  const [configData, setConfigData] = useState(null);
  const [targetWorkers, setTargetWorkers] = useState(1);
  const [targetRam, setTargetRam] = useState("4G");
  const [targetCores, setTargetCores] = useState(4);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/tuning/config');
      const data = await res.json();
      setConfigData(data);
      if (data.workers?.worker_count) {
        setTargetWorkers(data.workers.worker_count);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchConfig();
    const interval = setInterval(fetchConfig, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleApplyProfile = async (profileName) => {
    setLoading(true);
    try {
      const res = await fetch('/api/tuning/apply-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_name: profileName })
      });
      const data = await res.json();
      setMsg({ type: 'success', text: `Workload profile '${profileName}' applied across Spark & Livy!` });
      fetchConfig();
      if (onProfileChange) onProfileChange(profileName);
    } catch (ex) {
      setMsg({ type: 'error', text: `Failed: ${ex}` });
    } finally {
      setLoading(false);
    }
  };

  const handleScaleWorkers = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/tuning/scale-workers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worker_count: targetWorkers,
          worker_ram: targetRam,
          worker_cores: targetCores
        })
      });
      const data = await res.json();
      setMsg({ type: 'success', text: `Worker fleet scaled to ${targetWorkers} nodes!` });
      fetchConfig();
    } catch (ex) {
      setMsg({ type: 'error', text: `Failed: ${ex}` });
    } finally {
      setLoading(false);
    }
  };

  const metrics = configData?.metrics || { total_cores: 4, cores_used: 0, total_memory_mb: 4096, memory_used_mb: 0, alive_workers: 1 };
  const presets = configData?.presets || {};
  const activeProf = configData?.active_profile || 'Heavy Analytical';

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-amber-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            ⚙️ Spark Dynamic Resource Allocation (DRA) & Worker Node Scaler
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Fine-tune JVM heap allocations, broadcast join thresholds, off-heap caching, and horizontally scale the Spark worker container fleet dynamically.
          </p>
        </div>
        <button
          onClick={fetchConfig}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
          Poll Cluster
        </button>
      </div>

      {/* Status Feedback */}
      {msg && (
        <div className={`p-4 rounded-xl text-xs font-semibold border ${
          msg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {msg.text}
        </div>
      )}

      {/* METRIC CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card-sm p-4 border-l-4 border-l-indigo-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">Cluster Core Pool</div>
          <div className="text-2xl font-black text-white mt-1">{metrics.total_cores} Cores</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{metrics.cores_used} Cores Currently Allocated</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-sky-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-sky-400">Total Executor RAM</div>
          <div className="text-2xl font-black text-white mt-1">{(metrics.total_memory_mb / 1024).toFixed(1)} GB</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{(metrics.memory_used_mb / 1024).toFixed(1)} GB In Use</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-emerald-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-400">Active Worker Nodes</div>
          <div className="text-2xl font-black text-white mt-1">{metrics.alive_workers} Nodes</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Registered with Spark Master</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-amber-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-amber-400">Active Tuning Profile</div>
          <div className="text-lg font-black text-white mt-1 truncate">{activeProf}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Live on Port 7077</div>
        </div>
      </div>

      {/* WORKER FLEET SCALING CONTROLS */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-sky-400" />
          Horizontal Worker Node Fleet Scaler
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Target Worker Containers (1 – 8):</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="1"
                max="8"
                value={targetWorkers}
                onChange={(e) => setTargetWorkers(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <span className="font-mono text-sm font-black text-white px-3 py-1 rounded bg-slate-800 border border-white/10">
                {targetWorkers}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Memory Per Node:</label>
            <select
              value={targetRam}
              onChange={(e) => setTargetRam(e.target.value)}
              className="w-full bg-slate-950 border border-white/15 rounded-lg p-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="2G">2 GB RAM (Lightweight)</option>
              <option value="4G">4 GB RAM (Balanced)</option>
              <option value="8G">8 GB RAM (Heavy Workload)</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Cores Per Node:</label>
            <select
              value={targetCores}
              onChange={(e) => setTargetCores(parseInt(e.target.value))}
              className="w-full bg-slate-950 border border-white/15 rounded-lg p-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="2">2 CPU Cores</option>
              <option value="4">4 CPU Cores</option>
              <option value="8">8 CPU Cores</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleScaleWorkers}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-sky-500/20 flex items-center gap-2 transition disabled:opacity-50"
          >
            <Sliders className="w-3.5 h-3.5" />
            {loading ? 'Scaling Fleet...' : `Apply Scaling (${targetWorkers} Nodes • ${targetWorkers * parseInt(targetRam)}GB Total)`}
          </button>
        </div>
      </div>

      {/* WORKLOAD PROFILES GRID */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          Pre-Tuned Workload Architecture Profiles
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.keys(presets).map((pKey) => {
            const p = presets[pKey];
            const isCurrent = activeProf === pKey;

            return (
              <div
                key={pKey}
                className={`p-5 rounded-xl border transition-all ${
                  isCurrent
                    ? 'bg-indigo-950/30 border-indigo-500 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-900/60 border-white/[0.08] hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="font-bold text-sm text-white">{pKey}</div>
                  {isCurrent && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-mono font-bold">
                      ACTIVE
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-400 mt-1.5">{p.desc}</p>

                <div className="grid grid-cols-2 gap-2 mt-4 text-[11px] font-mono text-slate-300 bg-slate-950/70 p-3 rounded-lg border border-white/5">
                  <div>Driver: <span className="text-sky-400 font-bold">{p.driver_memory}</span></div>
                  <div>Executors: <span className="text-sky-400 font-bold">{p.executor_memory} ({p.executor_cores} cores)</span></div>
                  <div>Partitions: <span className="text-indigo-400 font-bold">{p.sql_shuffle_partitions}</span></div>
                  <div>Adaptive: <span className="text-emerald-400 font-bold">{p.adaptive_enabled ? 'ON' : 'OFF'}</span></div>
                </div>

                <div className="mt-4 flex justify-end">
                  <button
                    onClick={() => handleApplyProfile(pKey)}
                    disabled={isCurrent || loading}
                    className={`px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                      isCurrent
                        ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                        : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm shadow-indigo-600/20'
                    }`}
                  >
                    <CheckCircle2 className="w-3 h-3" />
                    {isCurrent ? 'Active Configuration' : 'Apply Profile'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
