import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  RotateCw, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  Cpu, 
  HardDrive, 
  ArrowRight,
  Zap,
  Sparkles,
  RefreshCw
} from 'lucide-react';

export default function PodOrchestrator({ services, presets, onRefresh }) {
  const [selectedPreset, setSelectedPreset] = useState("⚡ Spark Minimalist / PySpark Core");
  const [selectedCustom, setSelectedCustom] = useState(["hue"]);
  const [resolvedChain, setResolvedChain] = useState([]);
  const [tierFilter, setTierFilter] = useState("All Tiers");
  const [loadingAction, setLoadingAction] = useState(null);

  // Compute topological dependency resolution when custom selection changes
  useEffect(() => {
    if (selectedCustom.length > 0) {
      fetch('/api/orchestrator/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ services: selectedCustom })
      })
      .then(res => res.json())
      .then(data => setResolvedChain(data.resolved_services || []))
      .catch(err => console.error(err));
    } else {
      setResolvedChain([]);
    }
  }, [selectedCustom]);

  const handleStartServices = async (targets) => {
    setLoadingAction(`Starting ${targets.length} services...`);
    try {
      const res = await fetch('/api/orchestrator/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ services: targets })
      });
      const data = await res.json();
      onRefresh();
    } catch (ex) {
      alert(`Start failed: ${ex}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleStopServices = async (targets, cascade = true) => {
    setLoadingAction(`Stopping services...`);
    try {
      const res = await fetch('/api/orchestrator/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ services: targets, cascade })
      });
      const data = await res.json();
      onRefresh();
    } catch (ex) {
      alert(`Stop failed: ${ex}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRestartService = async (key) => {
    setLoadingAction(`Restarting ${key}...`);
    try {
      await fetch(`/api/orchestrator/restart/${key}`, { method: 'POST' });
      onRefresh();
    } catch (ex) {
      alert(`Restart failed: ${ex}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const tiers = ["All Tiers", "Foundation & Metadata", "Compute Engines", "Interactive Studios", "Security & Management"];
  const filteredServices = tierFilter === "All Tiers" ? services : services.filter(s => s.tier === tierFilter);

  const presetObj = presets[selectedPreset] || { desc: '', est_ram: '', services: [] };

  return (
    <div className="space-y-6">
      
      {/* Module Banner */}
      <div className="glass-card p-6 border-l-4 border-l-indigo-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            🎛️ Selective Pod Orchestrator & Dependency Lifecycle Manager
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Start only the components you need for your current workload. The orchestration engine automatically calculates transitive dependency graphs and starts required foundational services in exact sequence.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
          Sync Daemon
        </button>
      </div>

      {/* SECTION 1: 1-CLICK OPERATIONAL PRESETS */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wide uppercase text-indigo-400 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            1. 1-Click Operational Profiles
          </h3>
          <span className="text-xs text-slate-400">Pre-validated production workload presets</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {Object.keys(presets).map((pName) => {
            const isSelected = selectedPreset === pName;
            return (
              <button
                key={pName}
                onClick={() => setSelectedPreset(pName)}
                className={`p-3.5 rounded-xl text-left transition-all border ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-900/60 border-white/[0.08] hover:border-white/20 hover:bg-slate-800/40'
                }`}
              >
                <div className="font-bold text-xs text-white line-clamp-1">{pName}</div>
                <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">{presets[pName].desc}</div>
                <div className="text-[10px] font-mono text-sky-400 font-bold mt-2">{presets[pName].est_ram}</div>
              </button>
            );
          })}
        </div>

        {/* Selected Preset Action Strip */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-indigo-500/30 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-2">
              <span>{selectedPreset}</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">
                {presetObj.services?.length || 0} Pods
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5 flex-wrap">
              <span className="text-slate-500">Startup DAG Chain:</span>
              {presetObj.services?.map((s, i) => (
                <span key={s} className="flex items-center gap-1">
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">{s}</span>
                  {i < presetObj.services.length - 1 && <ArrowRight className="w-3 h-3 text-slate-600" />}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => handleStartServices(presetObj.services)}
              disabled={loadingAction !== null}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Launch Profile Fleet
            </button>
            <button
              onClick={() => handleStopServices(presetObj.services, true)}
              disabled={loadingAction !== null}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-rose-950/40 border border-white/10 hover:border-rose-500/40 text-slate-300 hover:text-rose-300 font-semibold text-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop Profile Fleet
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: LIVE TOPOLOGICAL DAG GRAPH BANNER */}
      {resolvedChain.length > 0 && (
        <div className="glass-card p-5 space-y-3 border border-indigo-500/30">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold uppercase tracking-wide text-sky-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              Topological Dependency Execution Graph
            </div>
            <span className="text-[11px] font-mono text-emerald-400">Ancestors resolved first</span>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-2 custom-scrollbar">
            {resolvedChain.map((node, idx) => (
              <div key={node.compose_service} className="flex items-center gap-2 flex-shrink-0">
                <div className="px-3 py-2 rounded-xl bg-slate-900/90 border border-white/10 text-center min-w-[120px]">
                  <div className="text-base">{node.icon}</div>
                  <div className="font-bold text-[11px] text-white mt-0.5">{node.name}</div>
                  <div className="text-[9px] font-mono text-slate-500">{node.compose_service}</div>
                </div>
                {idx < resolvedChain.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: LIVE SERVICE FLEET MATRIX */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
              📦 3. Live Cluster Service Fleet Matrix
            </h3>
            <span className="text-xs text-slate-400">15 Distributed Big Data containers • Real-time Docker socket binding</span>
          </div>

          {/* Architecture Tier Filters */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-white/10 overflow-x-auto">
            {tiers.map(t => (
              <button
                key={t}
                onClick={() => setTierFilter(t)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                  tierFilter === t ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Containers List */}
        <div className="space-y-2.5">
          {filteredServices.map(svc => {
            const isRunning = svc.status === "RUNNING";
            const isUnhealthy = svc.status === "UNHEALTHY";

            return (
              <div
                key={svc.key}
                className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.08] hover:border-white/15 transition flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4"
              >
                {/* Info */}
                <div className="flex items-center gap-3.5 min-w-[320px]">
                  <div className="text-2xl p-2 rounded-xl bg-slate-800/80 border border-white/10 flex-shrink-0">
                    {svc.icon}
                  </div>
                  <div>
                    <div className="font-extrabold text-sm text-white flex items-center gap-2">
                      {svc.name}
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-white/5">
                        {svc.compose_service}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5 max-w-xl line-clamp-1">{svc.desc}</div>
                  </div>
                </div>

                {/* Specs & Live Badge */}
                <div className="flex items-center gap-4 text-xs font-medium">
                  <div>
                    <span className={`px-2.5 py-1 rounded-full border text-[11px] font-bold ${
                      isRunning 
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-500/10'
                        : isUnhealthy
                        ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                        : 'bg-slate-800 border-white/10 text-slate-400'
                    }`}>
                      {svc.status}
                    </span>
                  </div>
                  <div className="text-slate-400 font-mono">
                    Port: <span className="text-white font-bold">{svc.port}</span>
                  </div>
                  <div className="text-slate-400 font-mono">
                    RAM: <span className="text-white font-bold">{svc.est_ram}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleStartServices([svc.key])}
                    disabled={isRunning || loadingAction !== null}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 font-bold text-xs flex items-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    Start
                  </button>
                  <button
                    onClick={() => handleStopServices([svc.key], false)}
                    disabled={!isRunning || loadingAction !== null}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/30 border border-white/10 hover:border-rose-500/30 text-slate-400 hover:text-rose-300 font-semibold text-xs flex items-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    Stop
                  </button>
                  <button
                    onClick={() => handleRestartService(svc.key)}
                    disabled={!isRunning || loadingAction !== null}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-400 hover:text-white transition disabled:opacity-40"
                    title="Restart Container"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
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
