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
  Table as TableIcon,
  ShieldCheck,
  Zap
} from 'lucide-react';

export default function DeltaMaintenance() {
  const [catalogTables, setCatalogTables] = useState([]);
  const [databases, setDatabases] = useState(['default']);
  const [selectedDb, setSelectedDb] = useState('default');
  const [selectedTable, setSelectedTable] = useState('inventory_delta');
  const [activeTab, setActiveTab] = useState('history'); // 'history', 'optimize', 'vacuum', 'restore'

  // Convert state
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertMsg, setConvertMsg] = useState(null);

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

  // Check table format from catalog metadata
  const selectedTableObj = catalogTables.find(t => 
    (t.database_name || t.Database || 'default') === selectedDb &&
    (t.table_name || t['Table Name']) === selectedTable
  );

  const isDeltaTable = Boolean(
    selectedTableObj?.format?.toLowerCase() === 'delta' ||
    selectedTableObj?.Provider?.toLowerCase() === 'delta' ||
    selectedTable?.includes('delta') ||
    selectedTable === 'rfid'
  );

  const handleConvertToDelta = async () => {
    if (!selectedTable) return;
    setConvertLoading(true);
    setConvertMsg(null);
    try {
      const res = await fetch('/api/delta/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          database: selectedDb,
          table: selectedTable
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Conversion failed");
      setConvertMsg({ type: 'success', text: `🎉 Table '${targetFullTable}' converted to Delta Lake format with ACID transaction log!` });
      await fetchTables();
      handleFetchHistory();
    } catch (err) {
      setConvertMsg({ type: 'error', text: `Conversion error: ${err.message}` });
    } finally {
      setConvertLoading(false);
    }
  };

  const handleFetchHistory = async () => {
    if (!selectedTable) return;
    setHistoryLoading(true);
    setHistoryLog(null);
    try {
      const res = await fetch(`/api/delta/history/${selectedDb}/${selectedTable}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch history");
      setHistoryLog(data.history_output || "Transaction history returned 0 commits.");
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
          version: parseInt(restoreVersion) || 0
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
      <div className="glass-card p-6 border-l-4 border-l-amber-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            ⏳ Delta Lake Time-Travel, Z-Ordering & VACUUM Maintenance
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Inspect ACID commit logs, query historic table snapshots with point-in-time time-travel (<code>VERSION AS OF</code>), execute file compaction & multidimensional Z-Ordering, reclaim dead storage, and perform in-place rollbacks.
          </p>
        </div>

        <button
          onClick={fetchTables}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition self-start md:self-auto"
          title="Refresh Metastore Tables"
        >
          <RefreshCw className="w-4 h-4 text-amber-400" />
        </button>
      </div>

      {/* Target Table Selector & In-Place Conversion Bar */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap flex-1">
            <div>
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Database</label>
              <select
                value={selectedDb}
                onChange={(e) => setSelectedDb(e.target.value)}
                className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
              >
                {databases.map(db => (
                  <option key={db} value={db}>{db}</option>
                ))}
              </select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Target Metastore Table</label>
              <select
                value={selectedTable}
                onChange={(e) => setSelectedTable(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
              >
                {tablesForSelectedDb.map(tbl => (
                  <option key={tbl} value={tbl}>{tbl}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 1-Click In-Place Convert to Delta Button */}
          <div className="flex items-end">
            <button
              onClick={handleConvertToDelta}
              disabled={convertLoading}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-indigo-600 hover:from-amber-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md transition flex items-center gap-1.5 disabled:opacity-50"
              title="Runs 'CONVERT TO DELTA' in-place without rewriting underlying parquet files"
            >
              {convertLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Converting to Delta Lake...
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5" />
                  Convert '{selectedTable}' to Delta Lake
                </>
              )}
            </button>
          </div>
        </div>

        {convertMsg && (
          <div className={`p-3 rounded-xl text-xs font-semibold border ${
            convertMsg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}>
            {convertMsg.text}
          </div>
        )}
      </div>

      {/* SUB-TABS NAVIGATION */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-2">
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'history' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white bg-slate-900/50'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          ACID Commit History
        </button>

        <button
          onClick={() => setActiveTab('optimize')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'optimize' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white bg-slate-900/50'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          File Compaction & Z-Ordering
        </button>

        <button
          onClick={() => setActiveTab('vacuum')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'vacuum' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white bg-slate-900/50'
          }`}
        >
          <Trash2 className="w-3.5 h-3.5" />
          VACUUM Storage Reclamation
        </button>

        <button
          onClick={() => setActiveTab('restore')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'restore' ? 'bg-amber-600 text-white shadow-lg' : 'text-slate-400 hover:text-white bg-slate-900/50'
          }`}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Point-in-Time Rollback
        </button>
      </div>

      {/* TAB 1: HISTORY & TIME-TRAVEL */}
      {activeTab === 'history' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* HISTORY INSPECTOR */}
          <div className="lg:col-span-7 glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  DESCRIBE HISTORY {targetFullTable}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Inspect transactional commit logs, operations, timestamps, and user provenance.
                </p>
              </div>
              <button
                onClick={handleFetchHistory}
                disabled={historyLoading}
                className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50"
              >
                {historyLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-white" />}
                Inspect Log
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/90 font-mono text-xs text-amber-300 border border-white/5 max-h-96 overflow-y-auto whitespace-pre custom-scrollbar">
              {historyLog || "Click 'Inspect Log' to view transactional history of commits."}
            </div>
          </div>

          {/* POINT-IN-TIME SNAPSHOT QUERY */}
          <div className="lg:col-span-5 glass-card p-6 space-y-4">
            <div className="border-b border-white/5 pb-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <Search className="w-4 h-4 text-sky-400" />
                Query Historical Snapshot
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Query table at exact historical version: <code>VERSION AS OF {'{version}'}</code>.
              </p>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Version Index</label>
                <input
                  type="number"
                  min="0"
                  value={versionInput}
                  onChange={(e) => setVersionInput(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <button
                onClick={handleFetchSnapshot}
                disabled={snapshotLoading}
                className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
              >
                {snapshotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Query Version {versionInput}
              </button>

              <div className="p-3 rounded-xl bg-slate-950 font-mono text-xs text-sky-300 border border-white/5 max-h-60 overflow-y-auto whitespace-pre custom-scrollbar">
                {snapshotData || "Results of historical snapshot query will appear here."}
              </div>
            </div>
          </div>

        </div>
      )}

      {/* TAB 2: OPTIMIZE & Z-ORDER */}
      {activeTab === 'optimize' && (
        <div className="glass-card p-6 space-y-5">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              File Compaction & Multidimensional Z-Ordering
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Compacts small Apache Parquet files into optimal ~1GB file sizes and co-locates multidimensional data points for up to 10x query speedups.
            </p>
          </div>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Z-Order Columns (Comma separated, optional):
              </label>
              <input
                type="text"
                placeholder="e.g. store_id, timestamp"
                value={zorderCols}
                onChange={(e) => setZorderCols(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <button
              onClick={handleOptimize}
              disabled={optimizeLoading}
              className="px-6 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-amber-600/30 disabled:opacity-50"
            >
              {optimizeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              ⚡ Run OPTIMIZE
            </button>
          </div>

          {optimizeResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-amber-300 whitespace-pre-wrap max-h-64 overflow-y-auto custom-scrollbar">
              {optimizeResult.error ? `Error: ${optimizeResult.error}` : optimizeResult.output}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: VACUUM STORAGE RECLAMATION */}
      {activeTab === 'vacuum' && (
        <div className="glass-card p-6 space-y-5">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-rose-400" />
              VACUUM Storage Reclamation
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Deletes data files no longer referenced by the latest Delta transaction log that are older than the retention threshold.
            </p>
          </div>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Retention Window (Hours):
              </label>
              <select
                value={retentionHours}
                onChange={(e) => setRetentionHours(parseInt(e.target.value) || 168)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-rose-500"
              >
                <option value={168}>168 Hours (7 Days - Standard Recommended)</option>
                <option value={72}>72 Hours (3 Days)</option>
                <option value={24}>24 Hours (1 Day)</option>
                <option value={0}>0 Hours (Immediate Purge)</option>
              </select>
            </div>

            <button
              onClick={handleVacuum}
              disabled={vacuumLoading}
              className="px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-rose-600/30 disabled:opacity-50"
            >
              {vacuumLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Execute VACUUM
            </button>
          </div>

          {vacuumResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-rose-300 whitespace-pre-wrap max-h-64 overflow-y-auto custom-scrollbar">
              {vacuumResult.error ? `Error: ${vacuumResult.error}` : (vacuumResult.output || "VACUUM completed successfully.")}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: POINT-IN-TIME ROLLBACK */}
      {activeTab === 'restore' && (
        <div className="glass-card p-6 space-y-5">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-purple-400" />
              Point-in-Time Table Rollback
            </h3>
            <p className="text-xs text-slate-300 mt-1">
              Restores a Delta Lake table in-place to an earlier point-in-time version commit.
            </p>
          </div>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Target Version to Rollback To:
              </label>
              <input
                type="number"
                min="0"
                value={restoreVersion}
                onChange={(e) => setRestoreVersion(parseInt(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              onClick={handleRestore}
              disabled={restoreLoading}
              className="px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-purple-600/30 disabled:opacity-50"
            >
              {restoreLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              Rollback Table to Version {restoreVersion}
            </button>
          </div>

          {restoreResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-purple-300 whitespace-pre-wrap max-h-64 overflow-y-auto custom-scrollbar">
              {restoreResult.error ? `Error: ${restoreResult.error}` : (restoreResult.output || `Table rolled back to version ${restoreVersion}.`)}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
