import React from 'react';
import { Activity, ExternalLink, Server, HardDrive, Cpu, Shield, Globe } from 'lucide-react';

export default function ClusterHealth({ services, onRefresh }) {
  const portals = [
    { name: 'Hue Analytics Web Studio', port: 8888, desc: 'Interactive SQL Editor, Hive Metastore & Table Explorer', icon: '🎨' },
    { name: 'Apache Spark Master Web UI', port: 8089, desc: 'Cluster Overview, Worker Nodes & Active Driver Applications', icon: '⚡' },
    { name: 'Spark History Server', port: 18080, desc: 'Completed DAG Stages, Task Metrics & Event Log Playback', icon: '📜' },
    { name: 'Hadoop HDFS NameNode Web UI', port: 9870, desc: 'Distributed File System Explorer & Block Storage Topology', icon: '📦' },
    { name: 'Hadoop YARN ResourceManager UI', port: 8088, desc: 'Distributed Memory Pool & Application Queue Manager', icon: '🐘' },
    { name: 'JupyterLab Data Science Workspace', port: 8889, desc: 'Interactive PySpark, Delta Lake & Lakehouse Notebooks', icon: '📓' },
    { name: 'MinIO S3 Object Storage Console', port: 9001, desc: 'S3 Buckets, Access Keys & Delta Lake Object Browser', icon: '🪣' },
    { name: 'pgAdmin 4 Database Console', port: 8081, desc: 'PostgreSQL Relational Metastore & Table Administrator', icon: '🛠️' },
    { name: 'Keycloak IAM & SSO Console', port: 8080, desc: 'Identity Provider & OAuth2 Lakehouse Security', icon: '🔐' },
  ];

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-emerald-500">
        <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-emerald-400" />
          BDP Cluster Infrastructure Health & Direct Portals
        </h2>
        <p className="text-xs text-slate-300 mt-1">
          Direct web interfaces and runtime diagnostics for all 15 distributed lakehouse services.
        </p>
      </div>

      {/* PORTALS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {portals.map((portal) => (
          <a
            key={portal.name}
            href={`http://localhost:${portal.port}`}
            target="_blank"
            rel="noreferrer"
            className="glass-card-sm p-5 border border-white/[0.08] hover:border-indigo-500/50 hover:bg-slate-900/90 transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-2xl">{portal.icon}</span>
                <span className="text-xs font-mono font-bold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                  :{portal.port}
                </span>
              </div>
              <div className="font-bold text-sm text-white mt-3 group-hover:text-indigo-300 transition">
                {portal.name}
              </div>
              <div className="text-xs text-slate-400 mt-1">{portal.desc}</div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs font-semibold text-slate-400 group-hover:text-white transition">
              <span>Open Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </div>
          </a>
        ))}
      </div>

    </div>
  );
}
