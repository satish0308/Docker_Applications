import React from 'react';
import { 
  Sliders, 
  Terminal, 
  UploadCloud, 
  Cpu, 
  Database, 
  Archive, 
  History, 
  Activity, 
  ScrollText, 
  Stethoscope, 
  Trash2, 
  BookOpen,
  Layers,
  ChevronRight
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const suites = [
    {
      title: "CORE PLATFORM ENGINE",
      items: [
        { id: "orchestrator", label: "Selective Pod Orchestrator", icon: Sliders, badge: "DAG" },
        { id: "sql_studio", label: "Persistent SQL Studio", icon: Terminal, badge: "Live" },
        { id: "ingestion", label: "Data Ingestion & Partitions", icon: UploadCloud },
        { id: "tuning", label: "Spark Dynamic Tuning", icon: Cpu, badge: "DRA" },
      ]
    },
    {
      title: "METASTORE & LAKEHOUSE",
      items: [
        { id: "metastore", label: "Metastore Catalog Browser", icon: Database },
        { id: "backup", label: "Disaster Recovery & Backup", icon: Archive },
        { id: "delta_time", label: "Delta Time-Travel & Vacuum", icon: History },
      ]
    },
    {
      title: "SYSTEM OBSERVABILITY",
      items: [
        { id: "health", label: "Cluster Health & Metrics", icon: Activity },
        { id: "logs", label: "Streaming Container Logs", icon: ScrollText, badge: "WS" },
        { id: "diagnostics", label: "Automated Port Diagnostics", icon: Stethoscope },
        { id: "purge", label: "1-Click Cluster Purge", icon: Trash2, danger: true },
      ]
    },
    {
      title: "KNOWLEDGE BASE",
      items: [
        { id: "docs", label: "Documentation & Runbooks", icon: BookOpen },
      ]
    }
  ];

  return (
    <aside className="w-72 flex-shrink-0 bg-[#07090e]/60 border-r border-white/[0.08] min-h-[calc(100vh-61px)] p-4 flex flex-col justify-between">
      <div className="space-y-6">
        {suites.map((suite, sIdx) => (
          <div key={sIdx} className="space-y-1.5">
            <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase px-3">
              {suite.title}
            </div>
            <div className="space-y-0.5">
              {suite.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all group ${
                      isActive
                        ? 'bg-gradient-to-r from-indigo-600/30 to-sky-500/20 text-white border border-indigo-500/40 shadow-sm shadow-indigo-500/10 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 transition ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${
                        isActive 
                          ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' 
                          : 'bg-slate-800 text-slate-400 border-white/5'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Cluster Specs Footer Card */}
      <div className="glass-card-sm p-3 border border-white/[0.08]">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Hadoop 3.3.6 • Spark 3.5.0</span>
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          15 Distributed Services • PostgreSQL Metastore • Delta Lake 3.0
        </div>
      </div>
    </aside>
  );
}
