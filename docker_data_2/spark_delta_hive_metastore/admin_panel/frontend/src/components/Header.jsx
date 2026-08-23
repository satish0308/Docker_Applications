import React from 'react';
import { Activity, ExternalLink, Zap, Server, Shield, Database, Terminal, Globe } from 'lucide-react';

export default function Header({ clusterOnline, unhealthyCount, wsConnected, activeProfile, services = [] }) {
  const portals = [
    { name: 'Hue', port: 8888, icon: '🎨', serviceKey: 'hue', color: 'hover:text-indigo-400 hover:border-indigo-500/40' },
    { name: 'Spark', port: 8089, icon: '⚡', serviceKey: 'spark', color: 'hover:text-sky-400 hover:border-sky-500/40' },
    { name: 'History', port: 18080, icon: '📜', serviceKey: 'spark', color: 'hover:text-amber-400 hover:border-amber-500/40' },
    { name: 'Jupyter', port: 8889, icon: '📓', serviceKey: 'jupyter', color: 'hover:text-emerald-400 hover:border-emerald-500/40' },
    { name: 'MinIO', port: 9001, icon: '🪣', serviceKey: 'minio', color: 'hover:text-rose-400 hover:border-rose-500/40' },
    { name: 'pgAdmin', port: 8081, icon: '🛠️', serviceKey: 'pgadmin', color: 'hover:text-purple-400 hover:border-purple-500/40' },
  ];

  const isServiceRunning = (key) => {
    const svc = services.find(s => 
      s.compose_service === key || 
      (s.name && s.name.toLowerCase().includes(key.toLowerCase())) ||
      (s.container_name && s.container_name.toLowerCase().includes(key.toLowerCase()))
    );
    return svc ? svc.status === 'RUNNING' : false;
  };

  return (
    <header className="sticky top-0 z-50 bg-[#07090e]/85 backdrop-blur-xl border-b border-white/[0.08] px-6 py-3">
      <div className="max-w-[1700px] mx-auto flex items-center justify-between">
        
        {/* Brand & Identity */}
        <div className="flex items-center gap-3.5">
          <div className="relative flex-shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-sky-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 font-black text-lg text-white">
              ⚡
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${wsConnected ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-sm tracking-tight text-white flex items-center gap-2">
                BDP CONTROL CENTER
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-bold tracking-wider">
                  v3.0 • REACT 18
                </span>
              </h1>
            </div>
            <p className="text-[11px] text-slate-400 font-medium line-clamp-1">
              Distributed Lakehouse Engine • Delta Lake, Apache Spark, Hive Metastore & YARN
            </p>
          </div>
        </div>

        {/* Global Telemetry & Status Badges (Uniform Height: h-8) */}
        <div className="flex items-center gap-2.5">
          
          {/* Active Profile Pill */}
          <div className="hidden lg:flex items-center gap-1.5 h-8 px-3 rounded-lg bg-slate-900/80 border border-white/10 text-xs font-medium">
            <Zap className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span className="text-slate-400">Profile:</span>
            <span className="font-semibold text-white truncate max-w-[120px]">{activeProfile || 'Heavy Analytical'}</span>
          </div>

          {/* WebSocket Push Status Pill */}
          <div className="hidden md:flex items-center gap-2 h-8 px-3 rounded-lg bg-slate-900/80 border border-white/10 text-xs font-medium">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${wsConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'}`}></div>
            <span className="font-mono text-[11px] text-slate-300">
              {wsConnected ? 'WebSocket: 0ms' : 'Connecting...'}
            </span>
          </div>

          {/* Health Pulse Status Pill */}
          <div className={`flex items-center gap-2 h-8 px-3 rounded-lg border text-xs font-semibold ${
            clusterOnline 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${clusterOnline ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span className="whitespace-nowrap">{clusterOnline ? 'Cluster Online' : `Server Unhealthy (${unhealthyCount})`}</span>
          </div>

          {/* Uniform Direct Web Portal Navigation Links with Live Indicator Bulbs */}
          <div className="flex items-center gap-1.5 pl-2.5 border-l border-white/10">
            {portals.map(p => {
              const running = isServiceRunning(p.serviceKey);
              return (
                <a
                  key={p.name}
                  href={`http://localhost:${p.port}`}
                  target="_blank"
                  rel="noreferrer"
                  className={`h-8 px-2.5 rounded-lg bg-slate-900/70 hover:bg-slate-800 border border-white/[0.08] text-xs font-medium text-slate-300 transition-all flex items-center gap-1.5 group ${p.color}`}
                  title={`Open ${p.name} (Port ${p.port}) • Status: ${running ? 'Running' : 'Stopped'}`}
                >
                  {/* Small Status Bulb */}
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    {running && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    )}
                    <span className={`relative inline-flex rounded-full h-2 w-2 ${
                      running ? 'bg-emerald-400 shadow-sm shadow-emerald-400/80' : 'bg-rose-500 shadow-sm shadow-rose-500/80'
                    }`}></span>
                  </span>

                  <span className="text-xs">{p.icon}</span>
                  <span>{p.name}</span>
                  <ExternalLink className="w-3 h-3 opacity-40 group-hover:opacity-100 transition flex-shrink-0" />
                </a>
              );
            })}
          </div>

        </div>

      </div>
    </header>
  );
}
