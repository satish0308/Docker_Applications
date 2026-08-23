import React from 'react';
import { Activity, ExternalLink, Zap, Server, Shield, Database, Terminal } from 'lucide-react';

export default function Header({ clusterOnline, unhealthyCount, wsConnected, activeProfile }) {
  const portals = [
    { name: 'Hue Studio', port: 8888, color: 'hover:text-indigo-400' },
    { name: 'Spark Master', port: 8089, color: 'hover:text-sky-400' },
    { name: 'History Server', port: 18080, color: 'hover:text-amber-400' },
    { name: 'JupyterLab', port: 8889, color: 'hover:text-emerald-400' },
    { name: 'MinIO Console', port: 9001, color: 'hover:text-rose-400' },
    { name: 'pgAdmin', port: 8081, color: 'hover:text-purple-400' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#07090e]/80 backdrop-blur-xl border-b border-white/[0.08] px-6 py-3.5">
      <div className="max-w-[1700px] mx-auto flex items-center justify-between">
        
        {/* Brand & Identity */}
        <div className="flex items-center gap-3.5">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-sky-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 font-black text-xl text-white">
              ⚡
            </div>
            <span className="absolute -bottom-1 -right-1 flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${wsConnected ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-extrabold text-base tracking-tight text-white flex items-center gap-2">
                BDP PLATFORM CONTROL CENTER
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-bold tracking-wider">
                  v3.0 • REACT 18 & FASTAPI
                </span>
              </h1>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              Distributed Lakehouse & Compute Engine • Delta Lake, Apache Spark, Hive Metastore & YARN
            </p>
          </div>
        </div>

        {/* Global Telemetry & Status Badges */}
        <div className="flex items-center gap-3">
          
          {/* Active Profile Pill */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-white/10 text-xs">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400">Profile:</span>
            <span className="font-semibold text-white">{activeProfile || 'Heavy Analytical'}</span>
          </div>

          {/* WebSocket Push Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-white/10 text-xs">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'}`}></div>
            <span className="font-mono text-[11px] text-slate-300">
              {wsConnected ? 'WebSocket: 0ms Real-Time Push' : 'WebSocket Reconnecting...'}
            </span>
          </div>

          {/* Health Pulse Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
            clusterOnline 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${clusterOnline ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            {clusterOnline ? 'Cluster Online' : `Server Unhealthy (${unhealthyCount} Down)`}
          </div>

          {/* Direct Web Portal Launchers */}
          <div className="hidden xl:flex items-center gap-1.5 pl-3 border-l border-white/10">
            {portals.map(p => (
              <a
                key={p.name}
                href={`http://localhost:${p.port}`}
                target="_blank"
                rel="noreferrer"
                className={`px-2.5 py-1 rounded-md bg-slate-800/40 hover:bg-slate-800 border border-white/[0.06] text-[11px] font-medium text-slate-300 transition flex items-center gap-1 ${p.color}`}
              >
                {p.name}
                <ExternalLink className="w-2.5 h-2.5 opacity-60" />
              </a>
            ))}
          </div>

        </div>

      </div>
    </header>
  );
}
