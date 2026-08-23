import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  Layers, 
  Sparkles, 
  Trash2, 
  RotateCcw, 
  Search, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Database,
  Calendar,
  FileText
} from 'lucide-react';

export default function DeltaMaintenance() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [activeTab, setActiveTab] = useState('history'); // 'history', 'optimize', 'vacuum', 'restore'

  // History / Snapshot state
  const [historyLog, setHistoryLog] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [versionInput, setVersionInput] = useState(0);
  const [snapshotData, setSnapshotData] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  // Optimize state
  const [zorderCols, setZorderCols] = useState('');
  const [optimizeLoading, setOptimizeLoading] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState(null);

  // Vacuum state
  const [retentionHours, setRetentionHours] = useState(168);
  const [vacuumLoading, setVacuumLoading] = useState(false);
  const [vacuumResult, setVacuumResult] = useState(null);

  // Restore state
  const [restoreVersion, setRestoreVersion] = useState(0);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreResult, setRestoreResult] = useState(null);

  useEffect(() => {
    fetch('/api/metastore/tables')
      .then(res => res.json())
      .then(data => {
        const tblList = (data.tables || []).map(t => `${t.Database}.${t['Table Name']}`);
        setTables(tblList);
        if (tblList.length > 0) {
          setSelectedTable(tblList[0]);
        }
      })
      .catch(err => console.error("Failed to load tables:", err));
  }, []);

  const getDbAndTable = () => {
    if (!selectedTable) return { db: 'default', table: 'sales' };
    const parts = selectedTable.split('.');
    return {
      db: parts[0] || 'default',
      table: parts[1] || parts[0]
    };
  };

  const handleFetchHistory = async () => {
    const { db, table } = getDbAndTable();
    setHistoryLoading(true);
    setHistoryLog(null);
    try {
      const res = await fetch(`/api/delta/history/${db}/${table}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch history");
      setHistoryLog(data.history_output);
    } catch (err) {
      setHistoryLog(`Error: ${err.message}`);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleFetchSnapshot = async () => {
    const { db, table } = getDbAndTable();
    setSnapshotLoading(true);
    setSnapshotData(null);
    try {
      const res = await fetch(`/api/delta/snapshot/${db}/${table}?version=${versionInput}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to query snapshot");
      setSnapshotData(data.snapshot_output);
    } catch (err) {
      setSnapshotData(`Error: ${err.message}`);
    } finally {
      setSnapshotLoading(false);
    }
  };

  const handleRunOptimize = async () => {
    const { db, table } = getDbAndTable();
    setOptimizeLoading(true);
    setOptimizeResult(null);
    try {
      const res = await fetch(`/api/delta/optimize/${db}/${table}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zorder_columns: zorderCols })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Optimization failed");
      setOptimizeResult(data);
    } catch (err) {
      setOptimizeResult({ error: err.message });
    } finally {
      setOptimizeLoading(false);
    }
  };

  const handleRunVacuum = async () => {
    const { db, table } = getDbAndTable();
    setVacuumLoading(true);
    setVacuumResult(null);
    try {
      const res = await fetch(`/api/delta/vacuum/${db}/${table}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ retention_hours: parseInt(retentionHours) || 168 })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Vacuum failed");
      setVacuumResult(data);
    } catch (err) {
      setVacuumResult({ error: err.message });
    } finally {
      setVacuumLoading(false);
    }
  };

  const handleRunRestore = async () => {
    const { db, table } = getDbAndTable();
    setRestoreLoading(true);
    setRestoreResult(null);
    try {
      const res = await fetch(`/api/delta/restore/${db}/${table}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: parseInt(restoreVersion) || 0 })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Restore failed");
      setRestoreResult(data);
    } catch (err) {
      setRestoreResult({ error: err.message });
    } finally {
      setRestoreLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-sky-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            ⏳ Delta Lake Time-Travel, Z-Ordering & VACUUM Maintenance
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Inspect ACID commit logs, query historic table snapshots with point-in-time time-travel (<code>VERSION AS OF</code>), execute file compaction & multidimensional Z-Ordering, reclaim dead storage, and perform in-place rollbacks.
          </p>
        </div>
      </div>

      {/* Table Selector & Tab Switcher Bar */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-indigo-400" />
            <div>
              <div className="text-xs font-bold text-slate-400">Target Delta Lake Table</div>
              {tables.length > 0 ? (
                <select
                  value={selectedTable}
                  onChange={(e) => setSelectedTable(e.target.value)}
                  className="bg-slate-900 border border-white/15 rounded-lg px-3 py-1.5 text-xs font-semibold text-white focus:outline-none focus:border-indigo-500 mt-1"
                >
                  {tables.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              ) : (
                <span className="text-xs font-mono text-slate-500">default.sales (default)</span>
              )}
            </div>
          </div>

          {/* Sub Tabs */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-white/10 overflow-x-auto">
            {[
              { id: 'history', label: '📜 Commit History', icon: Clock },
              { id: 'optimize', label: '⚡ Compaction & Z-Order', icon: Sparkles },
              { id: 'vacuum', label: '🧹 Vacuum Storage', icon: Trash2 },
              { id: 'restore', label: '⏪ In-Place Restore', icon: RotateCcw }
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                    isActive ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

        </div>
      </div>

      {/* TAB CONTENT 1: COMMIT HISTORY & TIME TRAVEL */}
      {activeTab === 'history' && (
        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                ACID Transaction Commit Log & Point-in-Time Snapshot
              </h3>
              <p className="text-xs text-slate-400 mt-1">Audit every Delta commit timestamp, operation metrics, and user metadata.</p>
            </div>
            <button
              onClick={handleFetchHistory}
              disabled={historyLoading}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-40"
            >
              {historyLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
              Fetch Commit History
            </button>
          </div>

          {historyLog && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto custom-scrollbar">
              <pre className="whitespace-pre-wrap">{historyLog}</pre>
            </div>
          )}

          <div className="pt-4 border-t border-white/10 space-y-4">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">Query Historical Snapshot (VERSION AS OF)</h4>
            <div className="flex items-center gap-3">
              <div className="w-48">
                <label className="text-[11px] text-slate-400 font-medium">Version Number</label>
                <input
                  type="number"
                  min="0"
                  value={versionInput}
                  onChange={(e) => setVersionInput(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-white/15 rounded-lg px-3 py-1.5 text-xs text-white mt-1 focus:outline-none focus:border-sky-500"
                />
              </div>
              <div className="pt-5">
                <button
                  onClick={handleFetchSnapshot}
                  disabled={snapshotLoading}
                  className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-40"
                >
                  {snapshotLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                  Query Snapshot at Version {versionInput}
                </button>
              </div>
            </div>

            {snapshotData && (
              <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-slate-300 max-h-64 overflow-y-auto custom-scrollbar">
                <pre className="whitespace-pre-wrap">{snapshotData}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT 2: OPTIMIZE & Z-ORDER */}
      {activeTab === 'optimize' && (
        <div className="glass-card p-6 space-y-5">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              File Compaction & Multidimensional Z-Ordering (OPTIMIZE)
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Coalesces small parquet files into optimized 1GB chunks and clusters multidimensional columns along a space-filling Hilbert curve.
            </p>
          </div>

          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-300">
              Z-Order Clustering Columns (Optional, comma-separated e.g. <code>customer_id, order_date</code>)
            </label>
            <input
              type="text"
              placeholder="e.g. store_id, transaction_date"
              value={zorderCols}
              onChange={(e) => setZorderCols(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-4 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <button
            onClick={handleRunOptimize}
            disabled={optimizeLoading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:opacity-90 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-40 shadow-lg shadow-indigo-500/20"
          >
            {optimizeLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            Execute OPTIMIZE Compaction
          </button>

          {optimizeResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Compaction Completed</span>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 whitespace-pre-wrap">{optimizeResult.output || JSON.stringify(optimizeResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 3: VACUUM STORAGE */}
      {activeTab === 'vacuum' && (
        <div className="glass-card p-6 space-y-5">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-amber-400" />
              Dead File Storage Reclamation (VACUUM)
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Deletes unreferenced snapshot parquet files older than the retention threshold to free up object storage and HDFS disk blocks.
            </p>
          </div>

          <div className="w-64 space-y-2">
            <label className="text-xs font-semibold text-slate-300">Retention Threshold (Hours)</label>
            <input
              type="number"
              min="0"
              value={retentionHours}
              onChange={(e) => setRetentionHours(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
            />
            <span className="text-[10px] text-slate-500 font-mono">168 hours = 7 days retention</span>
          </div>

          <button
            onClick={handleRunVacuum}
            disabled={vacuumLoading}
            className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-40 shadow-lg shadow-amber-500/20"
          >
            {vacuumLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
            Execute VACUUM Storage Cleanup
          </button>

          {vacuumResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Vacuum Cleanup Completed</span>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 whitespace-pre-wrap">{vacuumResult.output || JSON.stringify(vacuumResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 4: IN-PLACE RESTORE */}
      {activeTab === 'restore' && (
        <div className="glass-card p-6 space-y-5">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-rose-400 flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-rose-400" />
              1-Click In-Place Table Rollback & Restore
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Roll back accidental deletions or bad transformations by restoring the Delta table in-place to an exact earlier version ID.
            </p>
          </div>

          <div className="w-64 space-y-2">
            <label className="text-xs font-semibold text-slate-300">Target Restore Version ID</label>
            <input
              type="number"
              min="0"
              value={restoreVersion}
              onChange={(e) => setRestoreVersion(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-rose-500"
            />
          </div>

          <button
            onClick={handleRunRestore}
            disabled={restoreLoading}
            className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-40 shadow-lg shadow-rose-500/20"
          >
            {restoreLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
            Restore Table `{selectedTable}` in Place
          </button>

          {restoreResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Table Rollback Executed Successfully</span>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 whitespace-pre-wrap">{restoreResult.output || JSON.stringify(restoreResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
