import React, { useState, useEffect } from 'react';
import { 
  Archive, 
  RotateCcw, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Database, 
  ShieldCheck, 
  HardDrive, 
  Calendar, 
  FileCheck, 
  RefreshCw,
  FolderArchive,
  Table as TableIcon,
  Clock,
  Trash2,
  Sliders,
  PlusCircle,
  ToggleLeft,
  ToggleRight,
  Sparkles,
  Layers,
  History
} from 'lucide-react';

export default function BackupRestore() {
  const [activeSubTab, setActiveSubTab] = useState('manual'); // 'manual' | 'automated'
  const [backups, setBackups] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);

  // Metastore Catalog for Cascading Dropdowns
  const [catalogTables, setCatalogTables] = useState([]);
  const [databases, setDatabases] = useState(['default']);

  // Manual Backup Form State
  const [backupMode, setBackupMode] = useState('table'); // 'table' | 'database'
  const [database, setDatabase] = useState('default');
  const [table, setTable] = useState('sales');
  const [customId, setCustomId] = useState('');
  const [retentionLimit, setRetentionLimit] = useState(3);
  const [backupRunning, setBackupRunning] = useState(false);
  const [backupOutput, setBackupOutput] = useState(null);

  // Restore Form State
  const [selectedBackupId, setSelectedBackupId] = useState('');
  const [targetDb, setTargetDb] = useState('default');
  const [targetTable, setTargetTable] = useState('');
  const [storageDest, setStorageDest] = useState('s3a://warehouse/');
  const [restoreRunning, setRestoreRunning] = useState(false);
  const [restoreOutput, setRestoreOutput] = useState(null);

  // Auto-Backup Policy Creator Form State
  const [policyName, setPolicyName] = useState('');
  const [policyMode, setPolicyMode] = useState('database'); // 'database' | 'table'
  const [policyDb, setPolicyDb] = useState('default');
  const [policyTable, setPolicyTable] = useState('item_master');
  const [policyFrequency, setPolicyFrequency] = useState('1h'); // '1h' | '2h' | '6h' | '10h' | '24h'
  const [policyRetention, setPolicyRetention] = useState(3);
  const [policyCreating, setPolicyCreating] = useState(false);

  const fetchCatalog = async () => {
    try {
      const res = await fetch('/api/metastore/tables');
      const data = await res.json();
      const tblList = data.tables || [];
      setCatalogTables(tblList);

      const dbs = Array.from(new Set(tblList.map(t => t.database_name || t.Database || 'default')));
      if (dbs.length > 0) {
        setDatabases(dbs);
        if (!dbs.includes(database)) setDatabase(dbs[0]);
        if (!dbs.includes(policyDb)) setPolicyDb(dbs[0]);
      }
    } catch (err) {
      console.error("Failed to load metastore catalog:", err);
    }
  };

  const fetchBackups = async () => {
    setLoading(true);
    try {
      await fetchCatalog();
      const res = await fetch('/api/backup/list');
      const data = await res.json();
      const bList = data.backups || [];
      setBackups(bList);
      if (bList.length > 0 && !selectedBackupId) {
        setSelectedBackupId(bList[0].backup_id || '');
      }
    } catch (err) {
      console.error("Failed to fetch backups:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedules = async () => {
    try {
      const res = await fetch('/api/backup/schedules');
      const data = await res.json();
      setSchedules(data.schedules || []);
    } catch (err) {
      console.error("Failed to fetch backup schedules:", err);
    }
  };

  useEffect(() => {
    fetchBackups();
    fetchSchedules();
  }, []);

  // Tables filtered by chosen database (Manual Form)
  const tablesForDb = catalogTables
    .filter(t => (t.database_name || t.Database || 'default') === database)
    .map(t => t.table_name || t['Table Name']);

  useEffect(() => {
    if (tablesForDb.length > 0 && !tablesForDb.includes(table)) {
      setTable(tablesForDb[0]);
    }
  }, [database, catalogTables]);

  // Tables filtered by chosen database (Policy Form)
  const tablesForPolicyDb = catalogTables
    .filter(t => (t.database_name || t.Database || 'default') === policyDb)
    .map(t => t.table_name || t['Table Name']);

  useEffect(() => {
    if (tablesForPolicyDb.length > 0 && !tablesForPolicyDb.includes(policyTable)) {
      setPolicyTable(tablesForPolicyDb[0]);
    }
  }, [policyDb, catalogTables]);

  const handleRunBackup = async () => {
    setBackupRunning(true);
    setBackupOutput(null);
    try {
      const res = await fetch('/api/backup/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: backupMode,
          database,
          table: backupMode === 'table' ? table : null,
          custom_backup_id: customId || null,
          retention_count: retentionLimit
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Backup failed");
      setBackupOutput(data);
      fetchBackups();
    } catch (err) {
      setBackupOutput({ error: err.message });
    } finally {
      setBackupRunning(false);
    }
  };

  const handleRunRestore = async () => {
    if (!selectedBackupId) return;
    setRestoreRunning(true);
    setRestoreOutput(null);

    const chosenBackup = backups.find(b => b.backup_id === selectedBackupId);
    const isDb = chosenBackup?.backup_type === 'database';

    try {
      const res = await fetch('/api/backup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_id: selectedBackupId,
          mode: isDb ? 'database' : 'table',
          target_database: targetDb,
          target_table: isDb ? null : (targetTable || null),
          storage_dest: storageDest
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Restore failed");
      setRestoreOutput(data);
    } catch (err) {
      setRestoreOutput({ error: err.message });
    } finally {
      setRestoreRunning(false);
    }
  };

  const handleDeleteArchive = async (backupId) => {
    if (!window.confirm(`Are you sure you want to permanently delete backup snapshot '${backupId}'?`)) return;
    try {
      const res = await fetch(`/api/backup/${backupId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchBackups();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreatePolicy = async (e) => {
    e.preventDefault();
    setPolicyCreating(true);
    const defaultName = policyMode === 'database' 
      ? `Auto Backup: ${policyDb} DB (${policyFrequency})`
      : `Auto Backup: ${policyDb}.${policyTable} (${policyFrequency})`;

    try {
      const res = await fetch('/api/backup/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: policyName.trim() || defaultName,
          mode: policyMode,
          database: policyDb,
          table: policyMode === 'table' ? policyTable : null,
          frequency: policyFrequency,
          retention_count: parseInt(policyRetention, 10),
          storage_dest: 's3a://warehouse/'
        })
      });
      if (res.ok) {
        setPolicyName('');
        fetchSchedules();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setPolicyCreating(false);
    }
  };

  const handleTogglePolicy = async (scheduleId) => {
    try {
      await fetch(`/api/backup/schedules/${scheduleId}/toggle`, { method: 'POST' });
      fetchSchedules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeletePolicy = async (scheduleId) => {
    try {
      await fetch(`/api/backup/schedules/${scheduleId}`, { method: 'DELETE' });
      fetchSchedules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunPolicyNow = async (scheduleId) => {
    try {
      await fetch(`/api/backup/schedules/${scheduleId}/run-now`, { method: 'POST' });
      fetchSchedules();
      fetchBackups();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Sub-Tab Switcher */}
      <div className="glass-card p-6 border-l-4 border-l-purple-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Archive className="w-5 h-5 text-purple-400" />
            Disaster Recovery & Enterprise Backup Engine
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Deterministic table snapshots, database-level dumps, automated cron backups, and retention auto-pruning.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="bg-slate-900 border border-white/10 p-1 rounded-xl flex items-center gap-1">
            <button
              onClick={() => setActiveSubTab('manual')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'manual' 
                  ? 'bg-purple-600 text-white shadow-lg' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Manual Snapshot & Restore
            </button>
            <button
              onClick={() => setActiveSubTab('automated')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeSubTab === 'automated' 
                  ? 'bg-purple-600 text-white shadow-lg' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Automated Auto-Backup & Pruning ({schedules.length})
            </button>
          </div>

          <button
            onClick={() => { fetchBackups(); fetchSchedules(); }}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Refresh Backups & Policies"
          >
            <RefreshCw className={`w-4 h-4 text-purple-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SUB-TAB 1: MANUAL BACKUP & RESTORE                        */}
      {/* ========================================================= */}
      {activeSubTab === 'manual' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT: BACKUP EXECUTION PANEL */}
          <div className="lg:col-span-6 glass-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <FolderArchive className="w-4 h-4 text-purple-400" />
                1. Create Table / DB Backup
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                SHA-256 Protected
              </span>
            </div>

            {/* Scope Selection */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setBackupMode('table')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition ${
                  backupMode === 'table'
                    ? 'bg-purple-600/20 border-purple-500 text-purple-300'
                    : 'bg-slate-900/60 border-white/5 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                Single Table
              </button>
              <button
                type="button"
                onClick={() => setBackupMode('database')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition ${
                  backupMode === 'database'
                    ? 'bg-purple-600/20 border-purple-500 text-purple-300'
                    : 'bg-slate-900/60 border-white/5 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Full Database
              </button>
            </div>

            {/* Target Selectors */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Database Name</label>
                <select
                  value={database}
                  onChange={(e) => setDatabase(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                >
                  {databases.map(db => (
                    <option key={db} value={db}>{db}</option>
                  ))}
                </select>
              </div>

              {backupMode === 'table' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Table Name</label>
                  <select
                    value={table}
                    onChange={(e) => setTable(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                  >
                    {tablesForDb.map(tbl => (
                      <option key={tbl} value={tbl}>{tbl}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Custom Backup ID (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. backup_sales_q3_snapshot"
                  value={customId}
                  onChange={(e) => setCustomId(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Retention Limit (Auto-delete older backups)
                </label>
                <select
                  value={retentionLimit}
                  onChange={(e) => setRetentionLimit(parseInt(e.target.value, 10))}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:border-purple-500"
                >
                  <option value={1}>Keep Last 1 Snapshot (Replace Previous)</option>
                  <option value={3}>Keep Last 3 Snapshots (Recommended)</option>
                  <option value={5}>Keep Last 5 Snapshots</option>
                  <option value={10}>Keep Last 10 Snapshots</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleRunBackup}
              disabled={backupRunning}
              className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-purple-600/30 disabled:opacity-50"
            >
              {backupRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating Checksum Protected Backup...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Execute Backup Job
                </>
              )}
            </button>

            {backupOutput && (
              <div className="p-3 rounded-xl bg-slate-950/80 border border-white/10 text-xs font-mono max-h-40 overflow-y-auto custom-scrollbar">
                {backupOutput.error ? (
                  <span className="text-rose-400">{backupOutput.error}</span>
                ) : (
                  <pre className="text-emerald-400 whitespace-pre-wrap">{backupOutput.output}</pre>
                )}
              </div>
            )}
          </div>

          {/* RIGHT: RESTORE PANEL */}
          <div className="lg:col-span-6 glass-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-sky-400" />
                2. Restore from Backup
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                100% Integrity Validated
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Backup Snapshot Archive
                </label>
                <select
                  value={selectedBackupId}
                  onChange={(e) => setSelectedBackupId(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  {backups.length === 0 ? (
                    <option value="">No backups available</option>
                  ) : (
                    backups.map(b => (
                      <option key={b.backup_id} value={b.backup_id}>
                        {b.backup_id} ({b.table_name}) • {b.timestamp} • {b.size}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Database</label>
                <input
                  type="text"
                  value={targetDb}
                  onChange={(e) => setTargetDb(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Table (Optional override for single table)
                </label>
                <input
                  type="text"
                  placeholder="Leave empty to use original table name"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Storage Destination</label>
                <select
                  value={storageDest}
                  onChange={(e) => setStorageDest(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="s3a://warehouse/">MinIO S3 (s3a://warehouse/)</option>
                  <option value="hdfs://namenode:9000/user/hive/warehouse/">HDFS (hdfs://namenode:9000/...)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleRunRestore}
              disabled={restoreRunning || !selectedBackupId}
              className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-sky-600/30 disabled:opacity-50"
            >
              {restoreRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Verifying Checksums & Restoring Table...
                </>
              ) : (
                <>
                  <RotateCcw className="w-4 h-4" />
                  Execute Table / DB Restore
                </>
              )}
            </button>

            {restoreOutput && (
              <div className="p-3 rounded-xl bg-slate-950/80 border border-white/10 text-xs font-mono max-h-40 overflow-y-auto custom-scrollbar">
                {restoreOutput.error ? (
                  <span className="text-rose-400">{restoreOutput.error}</span>
                ) : (
                  <pre className="text-sky-400 whitespace-pre-wrap">{restoreOutput.output}</pre>
                )}
              </div>
            )}
          </div>

          {/* FULL WIDTH: AVAILABLE SNAPSHOT ARCHIVES */}
          <div className="lg:col-span-12 glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wide text-white flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-purple-400" />
                Available Backup Snapshots on Disk ({backups.length})
              </h3>
              <button
                onClick={fetchBackups}
                className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh Inventory
              </button>
            </div>

            {backups.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                No backup archives found. Generate a single table or full database snapshot above.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {backups.map(b => (
                  <div
                    key={b.backup_id}
                    className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-2 hover:border-purple-500/50 transition relative group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 uppercase">
                        {b.backup_type === 'database' ? '🗄️ Full Database' : '📦 Single Table'}
                      </span>
                      <button
                        onClick={() => handleDeleteArchive(b.backup_id)}
                        className="p-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition opacity-0 group-hover:opacity-100"
                        title="Delete Snapshot"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="font-bold text-xs text-white truncate" title={b.backup_id}>
                      {b.backup_id}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 pt-2 border-t border-white/5 font-mono">
                      <div>
                        <span className="text-slate-500">Database:</span> {b.database_name}
                      </div>
                      <div>
                        <span className="text-slate-500">Target:</span> {b.table_name}
                      </div>
                      <div>
                        <span className="text-slate-500">Size:</span> <span className="text-emerald-400 font-bold">{b.size}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Rows:</span> {typeof b.total_rows === 'number' ? b.total_rows.toLocaleString() : b.total_rows}
                      </div>
                      <div className="col-span-2 text-slate-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        {b.timestamp}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}

      {/* ========================================================= */}
      {/* SUB-TAB 2: AUTOMATED DISASTER RECOVERY & RETENTION ENGINE */}
      {/* ========================================================= */}
      {activeSubTab === 'automated' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT: POLICY CREATOR */}
          <div className="lg:col-span-5 glass-card p-6 space-y-5">
            <div className="border-b border-white/5 pb-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-emerald-400" />
                Configure Automated Backup Policy
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Creates recurring snapshots and automatically prunes older backups beyond the retention limit.
              </p>
            </div>

            <form onSubmit={handleCreatePolicy} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Policy Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Hourly Item Master Snapshot"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Scope Selection */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPolicyMode('database')}
                  className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                    policyMode === 'database'
                      ? 'bg-emerald-600/20 border-emerald-500 text-emerald-300'
                      : 'bg-slate-900/60 border-white/5 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <Database className="w-3.5 h-3.5" />
                  Full Database
                </button>
                <button
                  type="button"
                  onClick={() => setPolicyMode('table')}
                  className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                    policyMode === 'table'
                      ? 'bg-emerald-600/20 border-emerald-500 text-emerald-300'
                      : 'bg-slate-900/60 border-white/5 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <TableIcon className="w-3.5 h-3.5" />
                  Single Table
                </button>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Database</label>
                <select
                  value={policyDb}
                  onChange={(e) => setPolicyDb(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                >
                  {databases.map(db => (
                    <option key={db} value={db}>{db}</option>
                  ))}
                </select>
              </div>

              {policyMode === 'table' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Table</label>
                  <select
                    value={policyTable}
                    onChange={(e) => setPolicyTable(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                  >
                    {tablesForPolicyDb.map(tbl => (
                      <option key={tbl} value={tbl}>{tbl}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Frequency</label>
                  <select
                    value={policyFrequency}
                    onChange={(e) => setPolicyFrequency(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-bold text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="1h">Every 1 Hour (1h)</option>
                    <option value="2h">Every 2 Hours (2h)</option>
                    <option value="6h">Every 6 Hours (6h)</option>
                    <option value="10h">Every 10 Hours (10h)</option>
                    <option value="24h">Every Day / 24h (24h)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Retention Policy</label>
                  <select
                    value={policyRetention}
                    onChange={(e) => setPolicyRetention(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-bold text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value={1}>Keep 1 (Replace Old)</option>
                    <option value={2}>Keep Last 2</option>
                    <option value={3}>Keep Last 3</option>
                    <option value={5}>Keep Last 5</option>
                    <option value={10}>Keep Last 10</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={policyCreating}
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/30"
              >
                <PlusCircle className="w-4 h-4" />
                {policyCreating ? 'Registering Policy...' : 'Enable Automated Disaster Recovery Policy'}
              </button>
            </form>
          </div>

          {/* RIGHT: ACTIVE POLICIES LIST */}
          <div className="lg:col-span-7 glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-400" />
                  Active Auto-Backup Policies ({schedules.length})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Managed background daemon executes cron snapshots and applies retention pruning.
                </p>
              </div>
            </div>

            {schedules.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                No automated backup policies configured yet. Create a policy on the left.
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto custom-scrollbar">
                {schedules.map((s) => (
                  <div
                    key={s.schedule_id}
                    className="p-4 rounded-xl bg-slate-950/80 border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-emerald-500/40 transition"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-white">{s.name}</span>
                        <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {s.frequency.toUpperCase()}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-purple-500/10 text-purple-300 border border-purple-500/20">
                          Keep {s.retention_count}
                        </span>
                      </div>

                      <div className="text-[10px] text-slate-400 font-mono flex items-center gap-3">
                        <span>Target: {s.mode === 'database' ? `${s.database} (Full DB)` : `${s.database}.${s.table}`}</span>
                        <span>•</span>
                        <span>Next Run: {s.next_run || 'Pending'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-auto">
                      <button
                        onClick={() => handleRunPolicyNow(s.schedule_id)}
                        className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 text-[11px] font-bold border border-emerald-500/30 transition flex items-center gap-1"
                        title="Run Backup Now"
                      >
                        <Play className="w-3 h-3 fill-emerald-300" />
                        Run Now
                      </button>

                      <button
                        onClick={() => handleTogglePolicy(s.schedule_id)}
                        className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                        title={s.enabled ? "Pause Schedule" : "Resume Schedule"}
                      >
                        {s.enabled ? (
                          <ToggleRight className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <ToggleLeft className="w-5 h-5 text-slate-500" />
                        )}
                      </button>

                      <button
                        onClick={() => handleDeletePolicy(s.schedule_id)}
                        className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition"
                        title="Delete Policy"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}

    </div>
  );
}
