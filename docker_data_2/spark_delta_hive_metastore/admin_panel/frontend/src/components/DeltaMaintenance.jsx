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
  FileText,
  RefreshCw,
  Table as TableIcon
} from 'lucide-react';

export default function DeltaMaintenance() {
  const [catalogTables, setCatalogTables] = useState([]);
  const [databases, setDatabases] = useState(['default']);
  const [selectedDb, setSelectedDb] = useState('default');
  const [selectedTable, setSelectedTable] = useState('sales');
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

  const fetchTables = async () => {
    try {
      const res = await fetch('/api/metastore/tables');
      const data = await res.json();
      const tblList = data.tables || [];
      setCatalogTables(tblList);

      const dbs = Array.from(new Set(tblList.map(t => t.database_name || t.Database || 'default')));
      if (dbs.length > 0) {
        setDatabases(dbs);
        if (!dbs.includes(selectedDb)) {
          setSelectedDb(dbs[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load tables:", err);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  // Filter tables by selected database
  const tablesForSelectedDb = catalogTables
    .filter(t => (t.database_name || t.Database || 'default') === selectedDb)
    .map(t => t.table_name || t['Table Name']);

  useEffect(() => {
    if (tablesForSelectedDb.length > 0 && !tablesForSelectedDb.includes(selectedTable)) {
      setSelectedTable(tablesForSelectedDb[0]);
    }
  }, [selectedDb, catalogTables]);

  const targetFullTable = `${selectedDb}.${selectedTable}`;

  const handleFetchHistory = async () => {
    if (!selectedTable) return;
    setHistoryLoading(true);
    setHistoryLog(null);
    try {
      const res = await fetch(`/api/delta/history/${selectedDb}/${selectedTable}`);
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
    if (!selectedTable) return;
    setSnapshotLoading(true);
    setSnapshotData(null);
    try {
      const res = await fetch(`/api/delta/snapshot/${selectedDb}/${selectedTable}?version=${versionInput}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to query snapshot");
      setSnapshotData(data.snapshot_output);
    } catch (err) {
      setSnapshotData(`Error: ${err.message}`);
    } finally {
      setSnapshotLoading(false);
    }
  };

  const handleOptimize = async () => {
    if (!selectedTable) return;
    setOptimizeLoading(true);
    setOptimizeResult(null);
    try {
      const cols = zorderCols.split(',').map(c => c.trim()).filter(Boolean);
      const res = await fetch('/api/delta/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          database: selectedDb,
          table: selectedTable,
          zorder_by: cols
        })
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

  const handleVacuum = async () => {
    if (!selectedTable) return;
    setVacuumLoading(true);
    setVacuumResult(null);
    try {
      const res = await fetch('/api/delta/vacuum', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          database: selectedDb,
          table: selectedTable,
          retention_hours: parseInt(retentionHours) || 168
        })
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

  const handleRestore = async () => {
    if (!selectedTable) return;
    setRestoreLoading(true);
    setRestoreResult(null);
    try {
      const res = await fetch('/api/delta/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          database: selectedDb,
          table: selectedTable,
          target_version: parseInt(restoreVersion) || 0
        })
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
      
      {/* Header Banner */}
      <div className="glass-card p-6 border-l-4 border-l-amber-500">
        <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
          ⏳ Delta Lake Time-Travel, Z-Ordering & VACUUM Maintenance
        </h2>
        <p className="text-xs text-slate-300 mt-1 max-w-3xl">
          Inspect ACID commit logs, query historic table snapshots with point-in-time time-travel (<code>VERSION AS OF</code>), execute file compaction & multidimensional Z-Ordering, reclaim dead storage, and perform in-place rollbacks.
        </p>
      </div>

      {/* CASCADING DATABASE & TABLE SELECTOR */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-amber-400" />
              Target Lakehouse Database & Delta Table
            </label>
            <div className="text-[11px] text-slate-400">
              Selected Target: <span className="font-mono text-amber-300 font-bold">{targetFullTable}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Step 1: Database Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-900 border border-white/15 rounded-xl px-3 py-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400">Database:</span>
              <select
                value={selectedDb}
                onChange={(e) => setSelectedDb(e.target.value)}
                className="bg-transparent text-xs font-mono font-bold text-white focus:outline-none"
              >
                {databases.map(db => (
                  <option key={db} value={db} className="bg-slate-900">{db}</option>
                ))}
              </select>
            </div>

            {/* Step 2: Table Dropdown / Autocomplete */}
            <div className="flex items-center gap-1.5 bg-slate-900 border border-white/15 rounded-xl px-3 py-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400">Table:</span>
              {tablesForSelectedDb.length > 0 ? (
                <select
                  value={selectedTable}
                  onChange={(e) => setSelectedTable(e.target.value)}
                  className="bg-transparent text-xs font-mono font-bold text-sky-300 focus:outline-none"
                >
                  {tablesForSelectedDb.map(tbl => (
                    <option key={tbl} value={tbl} className="bg-slate-900">{tbl}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={selectedTable}
                  onChange={(e) => setSelectedTable(e.target.value)}
                  placeholder="e.g. sales"
                  className="bg-transparent text-xs font-mono font-bold text-sky-300 focus:outline-none w-28"
                />
              )}
            </div>

            <button
              onClick={fetchTables}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-300 hover:text-white transition"
              title="Refresh Metastore Tables"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-t border-white/10 pt-4 overflow-x-auto">
          {[
            { id: 'history', label: '📜 ACID Commit History', icon: Clock },
            { id: 'snapshot', label: '🕰️ Time-Travel Snapshot', icon: Calendar },
            { id: 'optimize', label: '⚡ OPTIMIZE & Z-Order', icon: Sparkles },
            { id: 'vacuum', label: '🧹 VACUUM Garbage Collection', icon: Trash2 },
            { id: 'restore', label: '🔄 In-Place Rollback', icon: RotateCcw }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 flex-shrink-0 ${
                  isActive 
                    ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/20' 
                    : 'bg-slate-900/60 text-slate-400 hover:text-white border border-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB CONTENTS */}

      {/* TAB 1: COMMIT HISTORY */}
      {activeTab === 'history' && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              ACID Commit Audit Trail & Lineage
            </h3>
            <button
              onClick={handleFetchHistory}
              disabled={historyLoading}
              className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              {historyLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
              Fetch Commit History
            </button>
          </div>

          {historyLog ? (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-amber-300 max-h-[480px] overflow-y-auto custom-scrollbar whitespace-pre-wrap">
              {historyLog}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
              Click "Fetch Commit History" to inspect transaction logs for <code>{targetFullTable}</code>.
            </div>
          )}
        </div>
      )}

      {/* TAB 2: TIME TRAVEL SNAPSHOT */}
      {activeTab === 'snapshot' && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-white">Point-In-Time Historical Snapshot</h3>
              <p className="text-xs text-slate-400 mt-0.5">Executes <code>SELECT * FROM {targetFullTable} VERSION AS OF {versionInput} LIMIT 50;</code></p>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-slate-900 border border-white/10 px-3 py-1.5 rounded-xl">
                <span className="text-xs text-slate-400 font-mono">Version:</span>
                <input
                  type="number"
                  value={versionInput}
                  onChange={(e) => setVersionInput(e.target.value)}
                  className="w-16 bg-transparent text-xs font-mono font-bold text-white focus:outline-none"
                  min="0"
                />
              </div>

              <button
                onClick={handleFetchSnapshot}
                disabled={snapshotLoading}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
              >
                {snapshotLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                Query Snapshot
              </button>
            </div>
          </div>

          {snapshotData && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-sky-300 max-h-[480px] overflow-y-auto custom-scrollbar whitespace-pre-wrap">
              {snapshotData}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: OPTIMIZE & Z-ORDER */}
      {activeTab === 'optimize' && (
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            File Compaction & Multidimensional Z-Ordering
          </h3>
          <p className="text-xs text-slate-300">
            Compacts small Apache Parquet files into optimal ~1GB file sizes and co-locates multidimensional data points for up to <b>10x query speedups</b>.
          </p>

          <div className="space-y-2 pt-2">
            <label className="text-xs font-bold text-slate-400">Z-Order Columns (Comma separated, optional):</label>
            <input
              type="text"
              value={zorderCols}
              onChange={(e) => setZorderCols(e.target.value)}
              placeholder="e.g. store_id, timestamp"
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-4 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleOptimize}
              disabled={optimizeLoading}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              {optimizeLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 fill-current" />}
              ⚡ Run OPTIMIZE
            </button>
          </div>

          {optimizeResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-emerald-300 whitespace-pre-wrap">
              {JSON.stringify(optimizeResult, null, 2)}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: VACUUM */}
      {activeTab === 'vacuum' && (
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-amber-400" />
            VACUUM Garbage Collection & Dead File Purge
          </h3>
          <p className="text-xs text-slate-300">
            Reclaims underlying HDFS/S3 storage capacity by deleting obsolete Parquet files no longer referenced by the Delta transaction log.
          </p>

          <div className="flex items-center gap-3 pt-2">
            <div className="flex items-center gap-2 bg-slate-900 border border-white/15 px-3.5 py-2 rounded-xl">
              <span className="text-xs text-slate-400 font-mono">Retention Hours:</span>
              <input
                type="number"
                value={retentionHours}
                onChange={(e) => setRetentionHours(e.target.value)}
                className="w-20 bg-transparent text-xs font-mono font-bold text-white focus:outline-none"
                min="0"
              />
            </div>

            <button
              onClick={handleVacuum}
              disabled={vacuumLoading}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              {vacuumLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              🧹 Run VACUUM
            </button>
          </div>

          {vacuumResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-emerald-300 whitespace-pre-wrap">
              {JSON.stringify(vacuumResult, null, 2)}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: IN-PLACE ROLLBACK */}
      {activeTab === 'restore' && (
        <div className="glass-card p-6 space-y-4 border border-rose-500/30">
          <h3 className="text-sm font-bold uppercase tracking-wider text-rose-400 flex items-center gap-2">
            <RotateCcw className="w-4 h-4" />
            In-Place ACID Version Rollback (RESTORE)
          </h3>
          <p className="text-xs text-slate-300">
            Reverts <code>{targetFullTable}</code> instantaneously back to an earlier historical commit without full data duplication.
          </p>

          <div className="flex items-center gap-3 pt-2">
            <div className="flex items-center gap-2 bg-slate-900 border border-white/15 px-3.5 py-2 rounded-xl">
              <span className="text-xs text-slate-400 font-mono">Target Version:</span>
              <input
                type="number"
                value={restoreVersion}
                onChange={(e) => setRestoreVersion(e.target.value)}
                className="w-20 bg-transparent text-xs font-mono font-bold text-white focus:outline-none"
                min="0"
              />
            </div>

            <button
              onClick={handleRestore}
              disabled={restoreLoading}
              className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              {restoreLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
              🔄 Execute In-Place Restore
            </button>
          </div>

          {restoreResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-emerald-300 whitespace-pre-wrap">
              {JSON.stringify(restoreResult, null, 2)}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
