import React, { useState, useEffect, useRef } from 'react';
import { 
  Cpu, 
  HardDrive, 
  Layers, 
  Zap, 
  Sliders, 
  CheckCircle2, 
  RefreshCw, 
  Server,
  Activity,
  Copy,
  Terminal,
  Settings,
  ShieldCheck,
  ExternalLink,
  SlidersHorizontal,
  FileCode,
  Gauge,
  Network
} from 'lucide-react';

export default function SparkTuning({ onProfileChange }) {
  const [configData, setConfigData] = useState(null);
  const [selectedProfileKey, setSelectedProfileKey] = useState('🔴 Heavy (Large Big Data / >10M Rows)');
  
  // Custom Fine-Grained Parameters State with LocalStorage & Server-State Retention
  const [customParams, setCustomParams] = useState(() => {
    const saved = localStorage.getItem('spark_custom_tuning_params');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      driver_memory: "4g",
      executor_memory: "8g",
      executor_cores: 4,
      max_cores: 8,
      dynamic_allocation: true,
      shuffle_partitions: 200,
      aqe_enabled: true,
      aqe_coalesce: true,
      memory_fraction: 0.8,
      storage_fraction: 0.4,
      offheap_enabled: true,
      offheap_size: "1g",
      kryo_serializer: true
    };
  });

  const customInitializedRef = useRef(false);
  const isEditingCustomRef = useRef(false);

  // Scaling Controls with LocalStorage & Server-State Retention
  const [targetWorkers, setTargetWorkers] = useState(() => {
    const saved = localStorage.getItem('spark_scaler_workers');
    return saved ? parseInt(saved, 10) : 4;
  });
  const [targetRam, setTargetRam] = useState(() => {
    const saved = localStorage.getItem('spark_scaler_ram');
    return saved || '4G';
  });
  const [targetCores, setTargetCores] = useState(() => {
    const saved = localStorage.getItem('spark_scaler_cores');
    return saved ? parseInt(saved, 10) : 4;
  });

  const scalerInitializedRef = useRef(false);

  // UI State
  const [activeSubTab, setActiveSubTab] = useState('profiles'); // 'profiles' | 'custom' | 'telemetry' | 'connections'
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [msg, setMsg] = useState(null);

  const fetchConfig = async (forceSync = false) => {
    try {
      const res = await fetch('/api/tuning/config');
      const data = await res.json();
      setConfigData(data);
      if (data.active_profile) {
        setSelectedProfileKey(data.active_profile);
      }

      // Only sync customParams on first load or on explicit user action, never during passive polling while user is editing
      if ((!customInitializedRef.current || forceSync) && data.active_params) {
        setCustomParams(prev => {
          const merged = { ...prev, ...data.active_params };
          // Clean offheap_size if disabled
          if (!merged.offheap_enabled || merged.offheap_size === "0") {
            merged.offheap_size = "1g"; // default standby size
            merged.offheap_enabled = data.active_params.offheap_enabled ?? false;
          }
          localStorage.setItem('spark_custom_tuning_params', JSON.stringify(merged));
          return merged;
        });
        customInitializedRef.current = true;
      }

      // Retain previously selected scaling values from server config on initial load
      if (!scalerInitializedRef.current && (data.worker_scaling || data.config?.worker_scaling)) {
        const sc = data.worker_scaling || data.config.worker_scaling;
        if (sc.worker_count) {
          setTargetWorkers(sc.worker_count);
          localStorage.setItem('spark_scaler_workers', sc.worker_count.toString());
        }
        if (sc.worker_ram) {
          const normRam = sc.worker_ram.toUpperCase();
          setTargetRam(normRam);
          localStorage.setItem('spark_scaler_ram', normRam);
        }
        if (sc.worker_cores) {
          setTargetCores(sc.worker_cores);
          localStorage.setItem('spark_scaler_cores', sc.worker_cores.toString());
        }
        scalerInitializedRef.current = true;
      }
    } catch (err) {
      console.error("Failed to load tuning configuration:", err);
    }
  };

  useEffect(() => {
    fetchConfig();
    const interval = setInterval(() => fetchConfig(false), 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectPreset = (presetKey) => {
    setSelectedProfileKey(presetKey);
    const presets = configData?.presets || {};
    if (presets[presetKey]) {
      const p = presets[presetKey];
      const updated = {
        ...p,
        dynamic_allocation: p.dynamic_allocation ?? true,
        offheap_enabled: Boolean(p.offheap_enabled),
        offheap_size: (p.offheap_size && p.offheap_size !== "0") ? p.offheap_size : "1g"
      };
      setCustomParams(updated);
      localStorage.setItem('spark_custom_tuning_params', JSON.stringify(updated));
    }
  };

  const updateParamField = (key, value) => {
    isEditingCustomRef.current = true;
    setCustomParams(prev => {
      const next = { ...prev, [key]: value };
      localStorage.setItem('spark_custom_tuning_params', JSON.stringify(next));
      return next;
    });
  };

  const handleApplyProfile = async (profileName, paramsToApply = null) => {
    setLoading(true);
    setMsg(null);
    try {
      const payloadParams = paramsToApply || customParams;
      // Normalize offheap size before sending
      const normalizedParams = {
        ...payloadParams,
        offheap_size: payloadParams.offheap_enabled ? (payloadParams.offheap_size || "1g") : "0"
      };

      const res = await fetch('/api/tuning/apply-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          profile_name: profileName,
          custom_params: normalizedParams
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to apply profile");
      
      localStorage.setItem('spark_custom_tuning_params', JSON.stringify(payloadParams));
      setMsg({ type: 'success', text: `🎉 Tuning profile '${profileName}' successfully applied across Spark Master, Livy, and Hue!` });
      await fetchConfig(true);
      if (onProfileChange) onProfileChange(profileName);
    } catch (ex) {
      setMsg({ type: 'error', text: `Failed: ${ex.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCustomOverride = () => {
    handleApplyProfile("🛠️ Custom Engine Override", customParams);
  };

  const handleWorkersSliderChange = (newCount) => {
    setTargetWorkers(newCount);
    localStorage.setItem('spark_scaler_workers', newCount.toString());
  };

  const handleRamChange = (newRam) => {
    setTargetRam(newRam);
    localStorage.setItem('spark_scaler_ram', newRam);
  };

  const handleCoresChange = (newCores) => {
    setTargetCores(newCores);
    localStorage.setItem('spark_scaler_cores', newCores.toString());
  };

  const handleScaleWorkers = async () => {
    setLoading(true);
    setMsg(null);
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
      if (!res.ok) throw new Error(data.detail || "Failed to scale workers");
      
      localStorage.setItem('spark_scaler_workers', targetWorkers.toString());
      localStorage.setItem('spark_scaler_ram', targetRam);
      localStorage.setItem('spark_scaler_cores', targetCores.toString());

      setMsg({ type: 'success', text: `Worker fleet scaled to ${targetWorkers} nodes with ${targetRam} RAM & ${targetCores} Cores each!` });
      fetchConfig(true);
    } catch (ex) {
      setMsg({ type: 'error', text: `Scaling Error: ${ex.message}` });
    } finally {
      setLoading(false);
    }
  };

  // Compile Dynamic spark-submit Command Line
  const buildGeneratedCommand = () => {
    const p = customParams || {};
    const dra = p.dynamic_allocation ? "true" : "false";
    const aqe = p.aqe_enabled ? "true" : "false";
    const aqeCoal = p.aqe_coalesce ? "true" : "false";

    let cmd = `/opt/spark/bin/spark-submit \\\n` +
      `  --driver-memory ${p.driver_memory || "4g"} \\\n` +
      `  --executor-memory ${p.executor_memory || "8g"} \\\n` +
      `  --conf spark.executor.cores=${p.executor_cores || 4} \\\n` +
      `  --conf spark.cores.max=${p.max_cores || 8} \\\n` +
      `  --conf spark.dynamicAllocation.enabled=${dra} \\\n` +
      `  --conf spark.dynamicAllocation.shuffleTracking.enabled=${dra} \\\n` +
      `  --conf spark.sql.shuffle.partitions=${p.shuffle_partitions || 200} \\\n` +
      `  --conf spark.sql.adaptive.enabled=${aqe} \\\n` +
      `  --conf spark.sql.adaptive.coalescePartitions.enabled=${aqeCoal} \\\n` +
      `  --conf spark.memory.fraction=${p.memory_fraction || 0.8} \\\n` +
      `  --conf spark.memory.storageFraction=${p.storage_fraction || 0.4}`;

    if (p.offheap_enabled) {
      cmd += ` \\\n  --conf spark.memory.offHeap.enabled=true \\\n  --conf spark.memory.offHeap.size=${(p.offheap_size && p.offheap_size !== "0") ? p.offheap_size : "1g"}`;
    }
    if (p.kryo_serializer) {
      cmd += ` \\\n  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer`;
    }
    cmd += ` \\\n  <job_script.py>`;
    return cmd;
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const metrics = configData?.metrics || { 
    total_cores: 4, 
    cores_used: 0, 
    total_memory_mb: 4096, 
    memory_used_mb: 0, 
    alive_workers: 1,
    worker_list: [],
    active_apps: []
  };
  const presets = configData?.presets || {};
  const activeProf = configData?.active_profile || '🔴 Heavy (Large Big Data / >10M Rows)';
  const connections = configData?.connections || {
    spark_rpc: "spark://spark:7077",
    spark_master_ui: "http://localhost:8089",
    spark_history_ui: "http://localhost:18080",
    spark_thriftserver: "localhost:10000",
    livy_rest_api: "http://localhost:8998",
    hdfs_namenode: "hdfs://namenode:9000"
  };

  // Memory Options: Max 20 GB with increment of 2 GB
  const ramOptions = ["2G", "4G", "6G", "8G", "10G", "12G", "14G", "16G", "18G", "20G"];
  const coresOptions = [1, 2, 4, 6, 8, 12, 16];

  return (
    <div className="space-y-6">
      
      {/* Header Banner & Sub-Tab Navigation */}
      <div className="glass-card p-6 border-l-4 border-l-amber-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            Spark Performance Tuning & Dynamic Resource Allocation (DRA)
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Sizing presets, fine-grained JVM parameter tuning, Kryo/AQE switches, live cluster metrics, and horizontal worker fleet scaling.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="bg-slate-900 border border-white/10 p-1 rounded-xl flex items-center gap-1">
            <button
              onClick={() => setActiveSubTab('profiles')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'profiles' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Presets & Profiles
            </button>
            <button
              onClick={() => setActiveSubTab('custom')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'custom' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Fine-Grained Tuner
            </button>
            <button
              onClick={() => setActiveSubTab('telemetry')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'telemetry' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              Cluster Telemetry ({metrics.alive_workers})
            </button>
            <button
              onClick={() => setActiveSubTab('connections')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'connections' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Connection URIs
            </button>
          </div>

          <button
            onClick={() => fetchConfig(true)}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Poll Cluster State"
          >
            <RefreshCw className="w-4 h-4 text-amber-400" />
          </button>
        </div>
      </div>

      {/* Status Alert */}
      {msg && (
        <div className={`p-4 rounded-xl text-xs font-semibold border ${
          msg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {msg.text}
        </div>
      )}

      {/* CLUSTER CAPACITY METRICS STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card-sm p-4 border-l-4 border-l-indigo-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 flex items-center justify-between">
            <span>Cluster Core Pool</span>
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <div className="text-2xl font-black text-white mt-1">{metrics.total_cores} Cores</div>
          <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{metrics.cores_used} Allocated • {metrics.cores_free || Math.max(0, metrics.total_cores - metrics.cores_used)} Free</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-sky-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-sky-400 flex items-center justify-between">
            <span>Total Executor RAM</span>
            <HardDrive className="w-3.5 h-3.5" />
          </div>
          <div className="text-2xl font-black text-white mt-1">{(metrics.total_memory_mb / 1024).toFixed(1)} GB</div>
          <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{(metrics.memory_used_mb / 1024).toFixed(1)} GB In Use • {(metrics.memory_free_mb / 1024 || Math.max(0, (metrics.total_memory_mb - metrics.memory_used_mb) / 1024)).toFixed(1)} GB Free</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-emerald-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-400 flex items-center justify-between">
            <span>Active Worker Nodes</span>
            <Server className="w-3.5 h-3.5" />
          </div>
          <div className="text-2xl font-black text-white mt-1">{metrics.alive_workers} Nodes</div>
          <div className="text-[11px] text-slate-400 mt-0.5 font-mono">Registered on spark://spark:7077</div>
        </div>

        <div className="glass-card-sm p-4 border-l-4 border-l-amber-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-amber-400 flex items-center justify-between">
            <span>Active Tuning Profile</span>
            <Gauge className="w-3.5 h-3.5" />
          </div>
          <div className="text-sm font-black text-white mt-1 truncate" title={activeProf}>{activeProf}</div>
          <div className="text-[11px] text-emerald-400 mt-0.5 font-mono font-bold">🟢 Live in Master & Livy</div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SUB-TAB 1: WORKLOAD PROFILES & SIZING PRESETS             */}
      {/* ========================================================= */}
      {activeSubTab === 'profiles' && (
        <div className="space-y-6">
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold tracking-wide uppercase text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Pre-Tuned Workload Architecture Profiles
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Select a standardized performance blueprint engineered for specific data volumes and query complexities.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.keys(presets).map((pKey) => {
                const p = presets[pKey];
                const isCurrent = activeProf === pKey;

                return (
                  <div
                    key={pKey}
                    className={`p-5 rounded-2xl border transition flex flex-col justify-between ${
                      isCurrent
                        ? 'bg-amber-950/30 border-amber-500 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/50'
                        : 'bg-slate-900/60 border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="font-bold text-xs text-white truncate" title={pKey}>{pKey}</div>
                        {isCurrent && (
                          <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono font-bold">
                            CURRENT ACTIVE
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-300 leading-relaxed min-h-[40px]">
                        {p.description || p.desc}
                      </p>

                      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-300 bg-slate-950/80 p-3 rounded-xl border border-white/5">
                        <div>Driver: <span className="text-sky-400 font-bold">{p.driver_memory}</span></div>
                        <div>Executor: <span className="text-sky-400 font-bold">{p.executor_memory}</span></div>
                        <div>Cores/Exec: <span className="text-amber-400 font-bold">{p.executor_cores}</span></div>
                        <div>Max Cores: <span className="text-amber-400 font-bold">{p.max_cores}</span></div>
                        <div>Partitions: <span className="text-indigo-400 font-bold">{p.shuffle_partitions || p.sql_shuffle_partitions}</span></div>
                        <div>Allocation: <span className={`font-bold ${p.dynamic_allocation ? 'text-emerald-400' : 'text-slate-300'}`}>{p.dynamic_allocation ? 'DRA Auto' : 'Standalone'}</span></div>
                        <div>AQE Adaptive: <span className={`font-bold ${p.aqe_enabled ? 'text-emerald-400' : 'text-slate-400'}`}>{p.aqe_enabled ? 'ENABLED' : 'OFF'}</span></div>
                        <div>Off-Heap: <span className="text-purple-400 font-bold">{(p.offheap_enabled && p.offheap_size !== "0") ? p.offheap_size : 'OFF'}</span></div>
                        <div>Kryo: <span className="text-pink-400 font-bold">{p.kryo_serializer ? 'ON' : 'OFF'}</span></div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => {
                          handleSelectPreset(pKey);
                          setActiveSubTab('custom');
                        }}
                        className="text-xs text-slate-400 hover:text-white underline font-semibold transition"
                      >
                        Customize Parameters →
                      </button>

                      <button
                        onClick={() => handleApplyProfile(pKey, p)}
                        disabled={isCurrent || loading}
                        className={`px-4 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
                          isCurrent
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/5'
                            : 'bg-amber-600 hover:bg-amber-500 text-white shadow-md shadow-amber-600/30'
                        }`}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {isCurrent ? 'Active Configuration' : 'Apply Profile'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-TAB 2: FINE-GRAINED PARAMETER TUNER & OVERRIDE        */}
      {/* ========================================================= */}
      {activeSubTab === 'custom' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT: INTERACTIVE PARAMETER TUNER */}
          <div className="lg:col-span-7 glass-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-sky-400" />
                  Fine-Grained Engine Parameter Tuner
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Directly adjust JVM heap fractions, concurrency, serialization, off-heap cache, and shuffle partitions.
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                Persistent Hot-Reload
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Driver Memory</label>
                <select
                  value={customParams.driver_memory}
                  onChange={(e) => updateParamField('driver_memory', e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="1g">1 GB (Interactive / Debug)</option>
                  <option value="2g">2 GB (Standard)</option>
                  <option value="3g">3 GB (ETL Batch)</option>
                  <option value="4g">4 GB (Heavy Analytical)</option>
                  <option value="6g">6 GB (High Concurrency)</option>
                  <option value="8g">8 GB (Extreme Driver)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Executor Memory</label>
                <select
                  value={customParams.executor_memory}
                  onChange={(e) => updateParamField('executor_memory', e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="2g">2 GB (Light / Fits in 4G Worker)</option>
                  <option value="4g">4 GB (Balanced Standard)</option>
                  <option value="6g">6 GB (Wide Tables / High Joins)</option>
                  <option value="8g">8 GB (Heavy Big Data)</option>
                  <option value="10g">10 GB (High Memory Worker)</option>
                  <option value="12g">12 GB (Heavy Plus)</option>
                  <option value="16g">16 GB (Extreme Scale)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Executor Cores</label>
                <select
                  value={customParams.executor_cores}
                  onChange={(e) => updateParamField('executor_cores', parseInt(e.target.value, 10))}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value={1}>1 Core per Executor</option>
                  <option value={2}>2 Cores per Executor (Recommended)</option>
                  <option value={4}>4 Cores per Executor</option>
                  <option value={8}>8 Cores per Executor</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Max Total Cluster Cores</label>
                <select
                  value={customParams.max_cores}
                  onChange={(e) => updateParamField('max_cores', parseInt(e.target.value, 10))}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value={2}>2 Cores Total</option>
                  <option value={4}>4 Cores Total</option>
                  <option value={6}>6 Cores Total</option>
                  <option value={8}>8 Cores Total</option>
                  <option value={12}>12 Cores Total</option>
                  <option value={16}>16 Cores Total</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Shuffle Partitions</label>
                <select
                  value={customParams.shuffle_partitions}
                  onChange={(e) => updateParamField('shuffle_partitions', parseInt(e.target.value, 10))}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value={8}>8 Partitions (Small &lt;100MB)</option>
                  <option value={64}>64 Partitions (Standard ETL)</option>
                  <option value={200}>200 Partitions (Default Standard)</option>
                  <option value={300}>300 Partitions (High Concurrency)</option>
                  <option value={400}>400 Partitions (Large Big Data &gt;10M Rows)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Execution / Storage Fraction</label>
                <select
                  value={customParams.memory_fraction}
                  onChange={(e) => updateParamField('memory_fraction', parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value={0.6}>0.6 (60% Execution Heap)</option>
                  <option value={0.7}>0.7 (70% Execution Heap - Standard)</option>
                  <option value={0.8}>0.8 (80% Execution Heap - High Joins)</option>
                  <option value={0.85}>0.85 (85% Aggressive Execution)</option>
                </select>
              </div>
            </div>

            {/* Feature Flags Switches */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <label className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/90 border border-white/10 cursor-pointer hover:border-sky-500/40 transition">
                <input
                  type="checkbox"
                  checked={customParams.dynamic_allocation}
                  onChange={(e) => updateParamField('dynamic_allocation', e.target.checked)}
                  className="w-4 h-4 text-sky-600 rounded bg-slate-950 border-white/20 focus:ring-0"
                />
                <span className="text-xs text-slate-200 font-semibold">Dynamic Resource Allocation (DRA)</span>
              </label>

              <label className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/90 border border-white/10 cursor-pointer hover:border-sky-500/40 transition">
                <input
                  type="checkbox"
                  checked={customParams.aqe_enabled}
                  onChange={(e) => updateParamField('aqe_enabled', e.target.checked)}
                  className="w-4 h-4 text-sky-600 rounded bg-slate-950 border-white/20 focus:ring-0"
                />
                <span className="text-xs text-slate-200 font-semibold">Adaptive Query Execution (AQE)</span>
              </label>

              <label className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/90 border border-white/10 cursor-pointer hover:border-sky-500/40 transition">
                <input
                  type="checkbox"
                  checked={customParams.kryo_serializer}
                  onChange={(e) => updateParamField('kryo_serializer', e.target.checked)}
                  className="w-4 h-4 text-sky-600 rounded bg-slate-950 border-white/20 focus:ring-0"
                />
                <span className="text-xs text-slate-200 font-semibold">Kryo Fast Serialization</span>
              </label>

              {/* Off-Heap Toggle with Inline Sizing Selector */}
              <div className="p-3 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
                <label className="flex items-center justify-between cursor-pointer">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={Boolean(customParams.offheap_enabled)}
                      onChange={(e) => {
                        const isChecked = e.target.checked;
                        const defaultSize = (customParams.offheap_size && customParams.offheap_size !== "0") ? customParams.offheap_size : "1g";
                        setCustomParams(prev => {
                          const next = {
                            ...prev,
                            offheap_enabled: isChecked,
                            offheap_size: isChecked ? defaultSize : "0"
                          };
                          localStorage.setItem('spark_custom_tuning_params', JSON.stringify(next));
                          return next;
                        });
                      }}
                      className="w-4 h-4 text-purple-600 rounded bg-slate-950 border-white/20 focus:ring-0"
                    />
                    <span className="text-xs text-slate-200 font-semibold">Off-Heap Memory</span>
                  </div>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${customParams.offheap_enabled ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-slate-800 text-slate-500'}`}>
                    {customParams.offheap_enabled ? (customParams.offheap_size || '1g') : 'OFF'}
                  </span>
                </label>

                {customParams.offheap_enabled && (
                  <div className="pt-1">
                    <select
                      value={customParams.offheap_size || '1g'}
                      onChange={(e) => updateParamField('offheap_size', e.target.value)}
                      className="w-full bg-slate-950 border border-purple-500/40 rounded-lg px-2.5 py-1 text-xs font-mono text-purple-300 focus:outline-none"
                    >
                      <option value="1g">1 GB Off-Heap Cache (Standard)</option>
                      <option value="2g">2 GB Off-Heap Cache (High)</option>
                      <option value="4g">4 GB Off-Heap Cache (Extreme)</option>
                      <option value="8g">8 GB Off-Heap Cache (Heavy Cluster)</option>
                    </select>
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={handleSaveCustomOverride}
              disabled={loading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-sky-600 via-indigo-600 to-emerald-600 hover:opacity-90 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-sky-600/20"
            >
              <CheckCircle2 className="w-4 h-4" />
              {loading ? 'Propagating Configuration...' : '💾 Save & Apply Tuning Profile as Cluster Default'}
            </button>
          </div>

          {/* RIGHT: DYNAMIC SPARK-SUBMIT GENERATOR & SCALER */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* SPARK SUBMIT COMMAND CODE PREVIEW */}
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-emerald-400" />
                  Dynamic spark-submit Generator
                </h3>
                <button
                  onClick={() => copyToClipboard(buildGeneratedCommand())}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Copy className="w-3.5 h-3.5 text-emerald-400" />
                  {copied ? 'Copied!' : 'Copy Command'}
                </button>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950 font-mono text-xs text-emerald-400 border border-white/10 overflow-x-auto whitespace-pre leading-relaxed custom-scrollbar">
                {buildGeneratedCommand()}
              </div>
            </div>

            {/* HORIZONTAL WORKER NODE FLEET SCALER */}
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                    <Server className="w-4 h-4 text-sky-400" />
                    Horizontal Worker Fleet Scaler
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Scale from 1 to 8 container nodes with up to 20 GB RAM (increments of 2 GB).
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-1.5">
                    <span>Target Worker Containers:</span>
                    <span className="font-mono text-sky-400 font-bold px-2 py-0.5 rounded bg-slate-900 border border-white/10">
                      {targetWorkers} Nodes
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="8"
                    value={targetWorkers}
                    onChange={(e) => handleWorkersSliderChange(parseInt(e.target.value, 10))}
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
                    <span>1 Node</span>
                    <span>2</span>
                    <span>3</span>
                    <span>4</span>
                    <span>5</span>
                    <span>6</span>
                    <span>7</span>
                    <span>8 Nodes</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">RAM / Node (Max 20G • +2G)</label>
                    <select
                      value={targetRam}
                      onChange={(e) => handleRamChange(e.target.value)}
                      className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                    >
                      {ramOptions.map(ram => (
                        <option key={ram} value={ram}>{ram} RAM ({parseInt(ram)} GB / node)</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Cores / Node</label>
                    <select
                      value={targetCores}
                      onChange={(e) => handleCoresChange(parseInt(e.target.value, 10))}
                      className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                    >
                      {coresOptions.map(cores => (
                        <option key={cores} value={cores}>{cores} CPU Core{cores > 1 ? 's' : ''}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/80 border border-white/5 font-mono text-xs text-slate-300 flex items-center justify-between">
                  <span className="text-slate-400">Total Cluster Provisioning:</span>
                  <span className="text-emerald-400 font-bold">
                    {targetWorkers * parseInt(targetRam)} GB RAM • {targetWorkers * targetCores} Cores
                  </span>
                </div>

                <button
                  onClick={handleScaleWorkers}
                  disabled={loading}
                  className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-sky-600/30 disabled:opacity-50"
                >
                  <Server className="w-4 h-4" />
                  {loading ? 'Scaling Fleet Containers...' : `Apply Scaling (${targetWorkers} Nodes • ${targetWorkers * parseInt(targetRam)}GB Total)`}
                </button>
              </div>
            </div>

          </div>

        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-TAB 3: CLUSTER TELEMETRY & WORKER FLEET TABLE         */}
      {/* ========================================================= */}
      {activeSubTab === 'telemetry' && (
        <div className="space-y-6">
          
          {/* WORKER FLEET TABLE */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Server className="w-4 h-4 text-emerald-400" />
                  Active Registered Worker Fleet ({metrics.worker_list?.length || 0})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Live status, allocated memory, and CPU cores reported by Spark Master.
                </p>
              </div>
            </div>

            {(!metrics.worker_list || metrics.worker_list.length === 0) ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                No active workers registered on Spark Master. Check if spark-worker containers are running.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px]">
                      <th className="py-2.5 px-3">State</th>
                      <th className="py-2.5 px-3">Worker ID</th>
                      <th className="py-2.5 px-3">Host</th>
                      <th className="py-2.5 px-3">Cores (Used / Total)</th>
                      <th className="py-2.5 px-3">Memory (Used / Total)</th>
                      <th className="py-2.5 px-3 text-right">Web UI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    {metrics.worker_list.map((w, idx) => (
                      <tr key={w['Worker ID'] || idx} className="hover:bg-white/[0.02] transition">
                        <td className="py-3 px-3 font-bold text-emerald-400">{w.State || '🟢 ALIVE'}</td>
                        <td className="py-3 px-3 text-white font-bold truncate max-w-xs">{w['Worker ID']}</td>
                        <td className="py-3 px-3 text-slate-400">{w.Host}</td>
                        <td className="py-3 px-3">{w['Cores Used']} / {w.Cores} Cores</td>
                        <td className="py-3 px-3">{w['Memory Used (MB)']} / {w['Memory (MB)']} MB</td>
                        <td className="py-3 px-3 text-right">
                          <a
                            href={`http://localhost:${8091 + idx}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sky-400 hover:text-sky-300 font-bold inline-flex items-center gap-1"
                          >
                            Port {8091 + idx} <ExternalLink className="w-3 h-3" />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ACTIVE APPLICATIONS TABLE */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-sky-400" />
                  Live Master Telemetry & Running Applications ({metrics.active_apps?.length || 0})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Currently running driver sessions across Livy, Jupyter, and Spark-Submit.
                </p>
              </div>
            </div>

            {(!metrics.active_apps || metrics.active_apps.length === 0) ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                No active applications currently executing on cluster. Cluster is idle and ready for queries.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px]">
                      <th className="py-2.5 px-3">State</th>
                      <th className="py-2.5 px-3">App ID</th>
                      <th className="py-2.5 px-3">Name</th>
                      <th className="py-2.5 px-3">User</th>
                      <th className="py-2.5 px-3">Cores</th>
                      <th className="py-2.5 px-3">Memory / Slave</th>
                      <th className="py-2.5 px-3 text-right">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    {metrics.active_apps.map((a) => (
                      <tr key={a.id} className="hover:bg-white/[0.02] transition">
                        <td className="py-3 px-3 font-bold text-sky-400">{a.state}</td>
                        <td className="py-3 px-3 text-white font-bold">{a.id}</td>
                        <td className="py-3 px-3 text-amber-300">{a.name}</td>
                        <td className="py-3 px-3 text-slate-400">{a.user}</td>
                        <td className="py-3 px-3">{a.cores}</td>
                        <td className="py-3 px-3">{a.memoryperslave} MB</td>
                        <td className="py-3 px-3 text-right font-bold text-slate-300">{(a.duration / 1000).toFixed(1)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-TAB 4: CLUSTER CONNECTION STRINGS & ENDPOINTS         */}
      {/* ========================================================= */}
      {activeSubTab === 'connections' && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <Network className="w-4 h-4 text-sky-400" />
                Cluster Endpoint URIs & Connection Strings
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Exact connection strings for connecting external JDBC/ODBC, BI dashboards, Python SDKs, and pipelines.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">Spark Master RPC (Driver Submissions)</span>
                <button
                  onClick={() => copyToClipboard(connections.spark_rpc)}
                  className="text-slate-400 hover:text-white p-1 rounded bg-slate-800"
                  title="Copy URI"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="font-mono text-xs text-amber-400 font-bold bg-slate-900 p-2 rounded-lg border border-white/5">
                {connections.spark_rpc}
              </div>
              <p className="text-[11px] text-slate-400">Default RPC endpoint used by spark-submit and driver applications.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">Spark ThriftServer (HiveServer2 / JDBC)</span>
                <button
                  onClick={() => copyToClipboard(connections.spark_thriftserver)}
                  className="text-slate-400 hover:text-white p-1 rounded bg-slate-800"
                  title="Copy URI"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="font-mono text-xs text-sky-400 font-bold bg-slate-900 p-2 rounded-lg border border-white/5">
                jdbc:hive2://localhost:10000/default
              </div>
              <p className="text-[11px] text-slate-400">Connect DBeaver, Tableau, PowerBI, and Hue directly to Spark.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">Apache Livy REST API (Interactive Sessions)</span>
                <button
                  onClick={() => copyToClipboard(connections.livy_rest_api)}
                  className="text-slate-400 hover:text-white p-1 rounded bg-slate-800"
                  title="Copy URI"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="font-mono text-xs text-emerald-400 font-bold bg-slate-900 p-2 rounded-lg border border-white/5">
                {connections.livy_rest_api}
              </div>
              <p className="text-[11px] text-slate-400">RESTful interactive code execution used by Hue notebooks.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">HDFS NameNode Distributed Filesystem</span>
                <button
                  onClick={() => copyToClipboard(connections.hdfs_namenode)}
                  className="text-slate-400 hover:text-white p-1 rounded bg-slate-800"
                  title="Copy URI"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="font-mono text-xs text-purple-400 font-bold bg-slate-900 p-2 rounded-lg border border-white/5">
                {connections.hdfs_namenode}/user/hive/warehouse/
              </div>
              <p className="text-[11px] text-slate-400">Root storage location for external Hive Metastore tables.</p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
