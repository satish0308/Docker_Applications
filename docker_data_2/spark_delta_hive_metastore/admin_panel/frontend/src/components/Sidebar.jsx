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
  ChevronRight,
  Clock
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const suites = [
    {
      title: "🚀 DATA OPS & INGESTION",
      items: [
        { id: "ingestion", label: "Data Ingestion & Partitions", icon: UploadCloud },
        { id: "scheduled_jobs", label: "Scheduled Ingestion Jobs", icon: Clock },
        { id: "delta_time", label: "Delta Time-Travel & Vacuum", icon: History },
      ]
    },
    {
      title: "⚡ COMPUTE & SQL STUDIO",
      items: [
        { id: "orchestrator", label: "Selective Pod Orchestrator", icon: Sliders, badge: "DAG" },
        { id: "sql_studio", label: "Persistent SQL Studio", icon: Terminal, badge: "Live" },
        { id: "tuning", label: "Spark Dynamic Tuning", icon: Cpu, badge: "DRA" },
        { id: "diagnostics", label: "Automated Port Diagnostics", icon: Stethoscope },
      ]
    },
    {
      title: "📦 STORAGE & METASTORE",
      items: [
        { id: "metastore", label: "Metastore Catalog Browser", icon: Database },
        { id: "backup", label: "Disaster Recovery & Backup", icon: Archive },
      ]
    },
    {
      title: "📊 SYSTEM OBSERVABILITY",
      items: [
        { id: "health", label: "Cluster Health & Metrics", icon: Activity },
        { id: "logs", label: "Streaming Container Logs", icon: ScrollText, badge: "WS" },
        { id: "purge", label: "1-Click Cluster Purge", icon: Trash2, danger: true },
      ]
    },
    {
      title: "📚 KNOWLEDGE BASE",
      items: [
        { id: "docs", label: "Documentation & Runbooks", icon: BookOpen },
      ]
    }
  ];

  return (
    <aside className="w-72 flex-shrink-0 bg-[#07090e]/60 border-r border-white/[0.08] min-h-[calc(100vh-61px)] p-4 flex flex-col justify-between">
      <div className="space-y-5">
        {suites.map((suite, sIdx) => (
          <div key={sIdx} className="space-y-1">
            <div className="text-[10px] font-extrabold tracking-wider text-slate-500 uppercase px-3">
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
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition group ${
                      isActive 
                        ? 'bg-gradient-to-r from-indigo-600/30 to-sky-600/20 text-white border border-indigo-500/40 shadow-sm shadow-indigo-500/10' 
                        : item.danger
                        ? 'text-rose-400/80 hover:text-rose-300 hover:bg-rose-950/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className={`w-4 h-4 flex-shrink-0 ${
                        isActive ? 'text-indigo-400' : item.danger ? 'text-rose-400' : 'text-slate-500 group-hover:text-slate-300'
                      }`} />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge && (
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-full font-bold border ${
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

      {/* Footer Identity */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="font-bold text-slate-300">FastAPI Daemon</span>
          <span className="font-mono text-emerald-400 font-bold">● Active</span>
        </div>
        <div className="text-[10px] text-slate-500 font-mono">Port 8501 • Docker SDK 7.1</div>
      </div>
    </aside>
  );
}
