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
  RefreshCw,
  Loader2,
  Clock,
  Check,
  X
} from 'lucide-react';

export default function PodOrchestrator({ services, presets, onRefresh }) {
  const [selectedPreset, setSelectedPreset] = useState("⚡ Spark Minimalist / PySpark Core");
  const [selectedCustom, setSelectedCustom] = useState(["hue"]);
  const [resolvedChain, setResolvedChain] = useState([]);
  const [tierFilter, setTierFilter] = useState("All Tiers");

  // Live Streaming Pipeline State
  const [activePipeline, setActivePipeline] = useState(null); // { title: string, total: number, nodes: [], currentStep: number, logs: [], isFinished: boolean }

  // Compute topological dependency resolution for preview banner
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

  const runStreamingPipeline = async (url, payload, title) => {
    setActivePipeline({
      title,
      total: 0,
      nodes: [],
      currentStep: 0,
      logs: [`Initiating sequence orchestration for '${title}'...`],
      isFinished: false
    });

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep unfinished tail

        for (const block of lines) {
          if (block.startsWith('data: ')) {
            const jsonStr = block.replace('data: ', '').trim();
            if (!jsonStr) continue;
            try {
              const event = JSON.parse(jsonStr);

              if (event.type === 'INIT') {
                setActivePipeline(prev => ({
                  ...prev,
                  total: event.total,
                  nodes: event.nodes,
                  logs: [...prev.logs, `DAG sequence resolved: ${event.total} pods in dependency order.`]
                }));
              } else if (event.type === 'STEP_UPDATE') {
                setActivePipeline(prev => {
                  const updatedNodes = prev.nodes.map(n => {
                    if (n.key === event.key) {
                      return { ...n, status: event.status, msg: event.msg };
                    }
                    return n;
                  });

                  return {
                    ...prev,
                    currentStep: event.step,
                    nodes: updatedNodes,
                    logs: [...prev.logs, `[Step ${event.step}/${event.total}] ${event.key.toUpperCase()} ➔ ${event.status}: ${event.msg}`]
                  };
                });
              } else if (event.type === 'COMPLETE') {
                setActivePipeline(prev => ({
                  ...prev,
                  isFinished: true,
                  logs: [...prev.logs, `🎉 ${event.msg}`]
                }));
                onRefresh();
              }
            } catch (err) {
              console.error("SSE parse error", err);
            }
          }
        }
      }
    } catch (err) {
      setActivePipeline(prev => ({
        ...prev,
        isFinished: true,
        logs: [...(prev?.logs || []), `❌ Pipeline error: ${err}`]
      }));
    }
  };

  const handleStartPreset = (presetName) => {
    const targetServices = presets[presetName]?.services || [];
    runStreamingPipeline('/api/orchestrator/stream-start', { services: targetServices }, `Launch Profile: ${presetName}`);
  };

  const handleStopPreset = (presetName) => {
    const targetServices = presets[presetName]?.services || [];
    runStreamingPipeline('/api/orchestrator/stream-stop', { services: targetServices, cascade: true }, `Stop Profile: ${presetName}`);
  };

  const handleStartCustom = () => {
    runStreamingPipeline('/api/orchestrator/stream-start', { services: selectedCustom }, `Launch Custom DAG Selection (${selectedCustom.length} Pods)`);
  };

  const handleStopCustom = () => {
    runStreamingPipeline('/api/orchestrator/stream-stop', { services: selectedCustom, cascade: true }, `Stop Custom DAG Selection (${selectedCustom.length} Pods)`);
  };

  const handleRestartService = async (key) => {
    runStreamingPipeline('/api/orchestrator/stream-start', { services: [key] }, `Restart Service: ${key}`);
  };

  const tiers = ["All Tiers", "Foundation & Metadata", "Compute Engines", "Interactive Studios", "Security & Management"];
  const filteredServices = tierFilter === "All Tiers" ? services : services.filter(s => s.tier === tierFilter);

  const presetObj = presets[selectedPreset] || { desc: '', est_ram: '', services: [] };

  return (
    <div className="space-y-6">
      
      {/* Module Header */}
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
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
          Sync Daemon
        </button>
      </div>

      {/* ACTIVE REAL-TIME HORIZONTAL SEQUENCE PIPELINE GRAPH */}
      {activePipeline && (
        <div className="glass-card p-6 space-y-5 border-2 border-indigo-500/60 shadow-2xl shadow-indigo-500/20 bg-slate-950/90 relative animate-in fade-in zoom-in duration-300">
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {!activePipeline.isFinished ? (
                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              )}
              <h3 className="font-extrabold text-sm text-white tracking-wide">
                {activePipeline.title}
              </h3>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-slate-400">
                Step <span className="text-white font-bold">{activePipeline.currentStep}</span> / {activePipeline.total}
              </span>
              {activePipeline.isFinished && (
                <button
                  onClick={() => setActivePipeline(null)}
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
                  title="Close Pipeline View"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-white/10">
            <div 
              className="bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 h-2 transition-all duration-500"
              style={{ width: `${activePipeline.total > 0 ? (activePipeline.currentStep / activePipeline.total) * 100 : 5}%` }}
            />
          </div>

          {/* HORIZONTAL SEQUENCE NODES FLOW */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 overflow-x-auto custom-scrollbar">
            <div className="flex items-center gap-3 min-w-max pb-1">
              {activePipeline.nodes.map((node, index) => {
                const isPending = node.status === 'PENDING';
                const isStarting = node.status === 'STARTING' || node.status === 'STOPPING';
                const isRunning = node.status === 'RUNNING' || node.status === 'STOPPED';
                const isFailed = node.status === 'FAILED' || node.status === 'WARNING';

                return (
                  <React.Fragment key={node.key}>
                    <div className={`p-3.5 rounded-xl border flex flex-col items-center min-w-[140px] text-center transition-all duration-300 ${
                      isStarting
                        ? 'bg-indigo-950/70 border-indigo-400 shadow-lg shadow-indigo-500/30 ring-2 ring-indigo-400/50 scale-105'
                        : isRunning
                        ? 'bg-emerald-950/30 border-emerald-500/50 shadow-sm shadow-emerald-500/10'
                        : isFailed
                        ? 'bg-rose-950/40 border-rose-500/60'
                        : 'bg-slate-950/60 border-white/10 opacity-50'
                    }`}>
                      
                      <div className="relative">
                        <span className="text-2xl">{node.icon}</span>
                        {isStarting && (
                          <span className="absolute -top-1 -right-2 flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                          </span>
                        )}
                      </div>

                      <div className="font-extrabold text-xs text-white mt-1 line-clamp-1">{node.name}</div>
                      <div className="text-[10px] font-mono text-slate-400">{node.compose_service}</div>

                      {/* Dynamic Status Icon & Badge */}
                      <div className="mt-2.5">
                        {isStarting && (
                          <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-[10px] font-bold flex items-center gap-1">
                            <Loader2 className="w-2.5 h-2.5 animate-spin" />
                            Starting...
                          </span>
                        )}
                        {isRunning && (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold flex items-center gap-1">
                            <CheckCircle2 className="w-2.5 h-2.5" />
                            Ready
                          </span>
                        )}
                        {isPending && (
                          <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-white/5 text-[10px] font-medium flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5" />
                            Pending
                          </span>
                        )}
                        {isFailed && (
                          <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] font-bold flex items-center gap-1">
                            <AlertCircle className="w-2.5 h-2.5" />
                            Warning
                          </span>
                        )}
                      </div>

                    </div>

                    {index < activePipeline.nodes.length - 1 && (
                      <div className="flex items-center text-indigo-400 flex-shrink-0">
                        <ArrowRight className={`w-4 h-4 transition ${isStarting ? 'animate-pulse text-indigo-300 scale-125' : 'text-slate-600'}`} />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Live Step Execution Log Terminal */}
          <div className="p-3 bg-slate-950 rounded-xl border border-white/10 font-mono text-[11px] text-slate-300 max-h-36 overflow-y-auto custom-scrollbar leading-relaxed">
            {activePipeline.logs.map((log, idx) => (
              <div key={idx} className="hover:bg-white/[0.02]">
                <span className="text-slate-500 mr-2">›</span>
                {log}
              </div>
            ))}
          </div>

        </div>
      )}

      {/* SECTION 1: 1-CLICK OPERATIONAL PRESETS */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wide uppercase text-indigo-400 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            1. 1-Click Operational Profiles
          </h3>
          <span className="text-xs text-slate-400">Pre-validated production workload presets</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3">
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
                <div className="text-[10px] text-slate-400 mt-1 line-clamp-2">{presets[pName].desc}</div>
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
              onClick={() => handleStartPreset(selectedPreset)}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Launch Profile Fleet
            </button>
            <button
              onClick={() => handleStopPreset(selectedPreset)}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-rose-950/40 border border-white/10 hover:border-rose-500/40 text-slate-300 hover:text-rose-300 font-semibold text-xs flex items-center gap-2 transition"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop Profile Fleet
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: CUSTOM MULTI-SELECT WITH TOPOLOGICAL DAG RESOLVER */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wide uppercase text-sky-400 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-400" />
            2. Custom Pod Multi-Select & Real-Time DAG Resolver
          </h3>
          <span className="text-xs text-slate-400">Pick arbitrary pods; DAG auto-resolves missing dependencies</span>
        </div>

        {/* Pod Selector Chips */}
        <div className="flex flex-wrap gap-2">
          {services.map(svc => {
            const isSelected = selectedCustom.includes(svc.key);
            return (
              <button
                key={svc.key}
                onClick={() => {
                  if (isSelected) {
                    setSelectedCustom(selectedCustom.filter(k => k !== svc.key));
                  } else {
                    setSelectedCustom([...selectedCustom, svc.key]);
                  }
                }}
                className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition flex items-center gap-2 ${
                  isSelected
                    ? 'bg-indigo-600 text-white border-indigo-400 shadow-sm shadow-indigo-500/20'
                    : 'bg-slate-900/80 border-white/10 text-slate-400 hover:text-white hover:border-white/20'
                }`}
              >
                <span>{svc.icon}</span>
                <span>{svc.name}</span>
                {isSelected && <Check className="w-3 h-3" />}
              </button>
            );
          })}
        </div>

        {/* Resolved Chain Preview */}
        {resolvedChain.length > 0 && (
          <div className="p-4 rounded-xl bg-slate-900/90 border border-sky-500/30 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-300">
              <span>Resolved Sequence ({resolvedChain.length} Pods in strict dependency order):</span>
              <span className="text-sky-400 font-mono">Topological DFS Resolution</span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-1 custom-scrollbar">
              {resolvedChain.map((node, idx) => (
                <div key={node.compose_service} className="flex items-center gap-2 flex-shrink-0">
                  <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-white/10 text-xs font-mono text-white flex items-center gap-1.5">
                    <span>{node.icon}</span>
                    <span>{node.name}</span>
                  </div>
                  {idx < resolvedChain.length - 1 && (
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-white/5">
              <button
                onClick={handleStartCustom}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:opacity-90 text-white font-bold text-xs flex items-center gap-2 transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Start Selected Fleet & Upstream DAG
              </button>
              <button
                onClick={handleStopCustom}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-rose-950/40 border border-white/10 text-slate-300 hover:text-rose-300 font-semibold text-xs flex items-center gap-2 transition"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                Stop Selected & Cascade Downstream
              </button>
            </div>
          </div>
        )}
      </div>

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
                    onClick={() => runStreamingPipeline('/api/orchestrator/stream-start', { services: [svc.key] }, `Start: ${svc.name}`)}
                    disabled={isRunning}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 font-bold text-xs flex items-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    Start
                  </button>
                  <button
                    onClick={() => runStreamingPipeline('/api/orchestrator/stream-stop', { services: [svc.key], cascade: false }, `Stop: ${svc.name}`)}
                    disabled={!isRunning}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/30 border border-white/10 hover:border-rose-500/30 text-slate-400 hover:text-rose-300 font-semibold text-xs flex items-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    Stop
                  </button>
                  <button
                    onClick={() => handleRestartService(svc.key)}
                    disabled={!isRunning}
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
