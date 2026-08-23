import React, { useState, useEffect } from 'react';
import { 
  Stethoscope, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Activity, 
  Cpu, 
  Database, 
  Layers, 
  HardDrive, 
  Zap, 
  ShieldAlert, 
  ShieldCheck,
  Pause,
  Play,
  Server
} from 'lucide-react';

export default function Diagnostics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoProbe, setAutoProbe] = useState(true);
  const [filter, setFilter] = useState('enabled'); // 'enabled', 'all', 'degraded'
  const [tierFilter, setTierFilter] = useState('ALL');

  const runProbe = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/diagnostics/probe');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error("Diagnostics probe error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runProbe();
    let interval = null;
    if (autoProbe) {
      interval = setInterval(runProbe, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoProbe]);

  const summary = data?.summary || {
    total_probed: 0,
    enabled_count: 0,
    healthy: 0,
    degraded: 0,
    inactive: 0,
    avg_latency_ms: 0,
    cluster_status: 'IDLE'
  };

  const probes = data?.probes || [];

  const tiers = ['ALL', 'Foundation & Metadata', 'Compute Engines', 'Storage & Data', 'Interactive Analytics'];

  const filteredProbes = probes.filter(p => {
    // Status filter
    if (filter === 'enabled' && !p.is_enabled) return false;
    if (filter === 'degraded' && p.status !== 'DEGRADED') return false;

    // Tier filter
    if (tierFilter !== 'ALL' && p.tier !== tierFilter) return false;

    return true;
  });

  const isDegraded = summary.degraded > 0;

  return (
    <div className="space-y-6">
      
      {/* Executive Header Banner */}
      <div className={`glass-card p-6 border-l-4 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
        isDegraded 
          ? 'border-l-rose-500 bg-rose-950/10' 
          : 'border-l-emerald-500 bg-emerald-950/10'
      }`}>
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className={`w-3 h-3 rounded-full flex-shrink-0 relative ${
              isDegraded ? 'bg-rose-500' : 'bg-emerald-400'
            }`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isDegraded ? 'bg-rose-400' : 'bg-emerald-400'
              }`}></span>
            </div>
            <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
              Automated Multi-Port Network Socket Prober
            </h2>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              isDegraded 
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' 
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
            }`}>
              {isDegraded ? `⚠️ ${summary.degraded} SERVICE(S) DEGRADED` : '🟢 ALL ACTIVE SERVICES HEALTHY'}
            </span>
          </div>
          <p className="text-xs text-slate-300 max-w-3xl">
            Continuously probes socket ports for <b>enabled / running cluster services</b>. Inactive services are automatically categorized without false positive alarms.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-shrink-0">
          <button
            onClick={() => setAutoProbe(!autoProbe)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition ${
              autoProbe 
                ? 'bg-sky-500/10 border-sky-500/30 text-sky-300 hover:bg-sky-500/20' 
                : 'bg-slate-800 border-white/10 text-slate-400 hover:text-white'
            }`}
          >
            {autoProbe ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            <span>{autoProbe ? 'Auto-Probe (5s)' : 'Paused'}</span>
          </button>

          <button
            onClick={runProbe}
            disabled={loading}
            className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-sky-600 hover:opacity-90 text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-500/20 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Probe Now</span>
          </button>
        </div>
      </div>

      {/* Metric Telemetry Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        
        <div className="glass-card p-4 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Active Services</div>
          <div className="text-xl font-black text-white font-mono">{summary.enabled_count}</div>
          <div className="text-[10px] text-slate-500">Currently running pods</div>
        </div>

        <div className="glass-card p-4 space-y-1 border-l-2 border-l-emerald-400">
          <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Healthy Ports</div>
          <div className="text-xl font-black text-emerald-400 font-mono">{summary.healthy}</div>
          <div className="text-[10px] text-slate-500">Sockets open & reachable</div>
        </div>

        <div className={`glass-card p-4 space-y-1 border-l-2 ${
          summary.degraded > 0 ? 'border-l-rose-500 bg-rose-950/20' : 'border-l-slate-700'
        }`}>
          <div className={`text-[10px] font-bold uppercase tracking-wider ${
            summary.degraded > 0 ? 'text-rose-400' : 'text-slate-400'
          }`}>
            Degraded Ports
          </div>
          <div className={`text-xl font-black font-mono ${
            summary.degraded > 0 ? 'text-rose-400' : 'text-slate-400'
          }`}>
            {summary.degraded}
          </div>
          <div className="text-[10px] text-slate-500">Connection refused / timeout</div>
        </div>

        <div className="glass-card p-4 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Disabled / Inactive</div>
          <div className="text-xl font-black text-slate-400 font-mono">{summary.inactive}</div>
          <div className="text-[10px] text-slate-500">Skipped in preset</div>
        </div>

        <div className="glass-card p-4 space-y-1">
          <div className="text-[10px] font-bold text-sky-400 uppercase tracking-wider">Avg Latency</div>
          <div className="text-xl font-black text-sky-400 font-mono">{summary.avg_latency_ms} <span className="text-xs font-normal">ms</span></div>
          <div className="text-[10px] text-slate-500">Internal bridge roundtrip</div>
        </div>

      </div>

      {/* Filter Toolbar */}
      <div className="glass-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Status Filter Toggle */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-white/10">
          {[
            { id: 'enabled', label: `🟢 Active (${summary.enabled_count})` },
            { id: 'degraded', label: `🔴 Degraded (${summary.degraded})` },
            { id: 'all', label: `📋 All Probes (${summary.total_probed})` }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                filter === t.id ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tier Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-400">Architecture Tier:</span>
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-slate-900 border border-white/15 rounded-xl px-3 py-1.5 text-xs font-bold text-white focus:outline-none focus:border-indigo-500"
          >
            {tiers.map(tr => (
              <option key={tr} value={tr}>{tr}</option>
            ))}
          </select>
        </div>

      </div>

      {/* PROBES GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredProbes.map((probe, idx) => {
          const isHealthy = probe.status === 'HEALTHY';
          const isDegraded = probe.status === 'DEGRADED';
          const isInactive = probe.status === 'INACTIVE';

          return (
            <div
              key={idx}
              className={`p-4 rounded-2xl border transition space-y-3 ${
                isHealthy
                  ? 'bg-slate-900/60 border-emerald-500/30 shadow-sm shadow-emerald-500/5'
                  : isDegraded
                  ? 'bg-rose-950/20 border-rose-500/50 shadow-md shadow-rose-500/10'
                  : 'bg-slate-950/40 border-white/5 opacity-50'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-extrabold text-xs text-white flex items-center gap-1.5">
                    <span>{probe.name}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {probe.desc}
                  </div>
                </div>

                {/* Status Badge */}
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border flex items-center gap-1 flex-shrink-0 ${
                  isHealthy
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : isDegraded
                    ? 'bg-rose-500/20 border-rose-500/40 text-rose-300 animate-pulse'
                    : 'bg-slate-800 border-white/10 text-slate-500'
                }`}>
                  {isHealthy && <CheckCircle2 className="w-3 h-3" />}
                  {isDegraded && <AlertCircle className="w-3 h-3" />}
                  {probe.status}
                </span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-white/5 space-y-1 font-mono text-[11px]">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Socket Target:</span>
                  <span className="text-slate-200 font-bold">{probe.host}:{probe.port}</span>
                </div>

                <div className="flex items-center justify-between text-slate-400">
                  <span>Container Pod:</span>
                  <span className="text-sky-300">{probe.container_name}</span>
                </div>

                {isHealthy && (
                  <div className="flex items-center justify-between text-slate-400 pt-1 border-t border-white/5">
                    <span>Response Latency:</span>
                    <span className="text-emerald-400 font-bold">{probe.latency_ms} ms</span>
                  </div>
                )}

                {isDegraded && (
                  <div className="pt-1 border-t border-rose-500/20 text-rose-400 text-[10px]">
                    Error: {probe.error || 'Connection refused / port closed'}
                  </div>
                )}

                {isInactive && (
                  <div className="pt-1 border-t border-white/5 text-slate-500 text-[10px]">
                    ⚪ Container is not started in current preset
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                <span>Tier: {probe.tier}</span>
                <span className={isHealthy ? 'text-emerald-400' : isDegraded ? 'text-rose-400' : 'text-slate-600'}>
                  {isHealthy ? '● Online' : isDegraded ? '● Failed' : '○ Standby'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
