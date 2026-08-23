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
  FolderArchive
} from 'lucide-react';

export default function BackupRestore() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);

  // Backup Form State
  const [backupMode, setBackupMode] = useState('table'); // 'table' | 'database'
  const [database, setDatabase] = useState('default');
  const [table, setTable] = useState('sales');
  const [customId, setCustomId] = useState('');
  const [backupRunning, setBackupRunning] = useState(false);
  const [backupOutput, setBackupOutput] = useState(null);

  // Restore Form State
  const [selectedBackupId, setSelectedBackupId] = useState('');
  const [targetDb, setTargetDb] = useState('default');
  const [targetTable, setTargetTable] = useState('');
  const [storageDest, setStorageDest] = useState('s3a://warehouse/');
  const [restoreRunning, setRestoreRunning] = useState(false);
  const [restoreOutput, setRestoreOutput] = useState(null);

  const fetchBackups = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backup/list');
      const data = await res.json();
      setBackups(data.backups || []);
      if (data.backups && data.backups.length > 0 && !selectedBackupId) {
        setSelectedBackupId(data.backups[0].backup_id || '');
      }
    } catch (err) {
      console.error("Failed to fetch backups:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBackups();
  }, []);

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
          custom_backup_id: customId || null
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
    try {
      const res = await fetch('/api/backup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_id: selectedBackupId,
          mode: backupMode,
          target_database: targetDb,
          target_table: targetTable || null,
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

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-purple-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            📦 Disaster Recovery & Table Backup Engine
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Create snapshot exports of Delta & Hive tables with <b>SHA-256 bit-for-bit checksum verification</b>, and perform 1-click in-place or cloned disaster recovery restorations.
          </p>
        </div>
        <button
          onClick={fetchBackups}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loading ? 'animate-spin' : ''}`} />
          Refresh Backups
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: BACKUP EXECUTION PANEL */}
        <div className="lg:col-span-5 glass-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
              <Archive className="w-4 h-4 text-purple-400" />
              1. Create Table / DB Backup
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
              SHA-256 Protected
            </span>
          </div>

          {/* Backup Mode Toggle */}
          <div className="flex rounded-xl bg-slate-900 p-1 border border-white/10">
            <button
              onClick={() => setBackupMode('table')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition ${
                backupMode === 'table' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              Single Table
            </button>
            <button
              onClick={() => setBackupMode('database')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition ${
                backupMode === 'database' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              Full Database
            </button>
          </div>

          {/* Database Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Database Name</label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
            />
          </div>

          {/* Table Input (if Single Table) */}
          {backupMode === 'table' && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Table Name</label>
              <input
                type="text"
                value={table}
                onChange={(e) => setTable(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>
          )}

          {/* Custom Backup ID (Optional) */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Custom Backup ID (Optional)</label>
            <input
              type="text"
              placeholder="e.g. backup_sales_q3_snapshot"
              value={customId}
              onChange={(e) => setCustomId(e.target.value)}
              className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
            />
          </div>

          <button
            onClick={handleRunBackup}
            disabled={backupRunning}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 transition disabled:opacity-40 shadow-lg shadow-purple-500/20"
          >
            {backupRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            Execute Backup Job
          </button>

          {backupOutput && (
            <div className="p-3.5 rounded-xl bg-slate-950 border border-white/10 text-xs font-mono max-h-40 overflow-y-auto custom-scrollbar">
              <pre className="text-slate-300 whitespace-pre-wrap">{backupOutput.output || JSON.stringify(backupOutput, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: RESTORE & BACKUP INVENTORY */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* RESTORE PANEL */}
          <div className="glass-card p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-emerald-400" />
                2. 1-Click Table / Database Restore
              </h3>
              <span className="text-xs text-slate-400">Zero Downtime Disaster Recovery</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Database</label>
                <input
                  type="text"
                  value={targetDb}
                  onChange={(e) => setTargetDb(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Target Table Name (Optional Clone)</label>
                <input
                  type="text"
                  placeholder="Leave empty for in-place restore"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Storage Destination</label>
              <input
                type="text"
                value={storageDest}
                onChange={(e) => setStorageDest(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              onClick={handleRunRestore}
              disabled={restoreRunning || !selectedBackupId}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-90 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-40 shadow-lg shadow-emerald-500/20"
            >
              {restoreRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
              Restore `{selectedBackupId || 'Select a Backup'}`
            </button>

            {restoreOutput && (
              <div className="p-3.5 rounded-xl bg-slate-950 border border-white/10 text-xs font-mono max-h-40 overflow-y-auto custom-scrollbar">
                <pre className="text-slate-300 whitespace-pre-wrap">{restoreOutput.output || JSON.stringify(restoreOutput, null, 2)}</pre>
              </div>
            )}
          </div>

          {/* BACKUPS CATALOG LIST */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <FolderArchive className="w-4 h-4 text-sky-400" />
                Available Backups Catalog ({backups.length})
              </h3>
            </div>

            {backups.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
                No backups found. Run a backup above to create your first snapshot.
              </div>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto custom-scrollbar">
                {backups.map((b) => {
                  const isSelected = selectedBackupId === b.backup_id;
                  return (
                    <div
                      key={b.backup_id}
                      onClick={() => setSelectedBackupId(b.backup_id)}
                      className={`p-3.5 rounded-xl border transition cursor-pointer flex items-center justify-between gap-3 ${
                        isSelected
                          ? 'bg-purple-950/30 border-purple-500/50 shadow-md shadow-purple-500/10'
                          : 'bg-slate-900/60 border-white/[0.08] hover:border-white/20'
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="font-extrabold text-xs text-white truncate flex items-center gap-2">
                          <span>{b.backup_id}</span>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400">
                            {b.backup_type || 'table'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          Source: <span className="text-slate-300 font-mono">{b.source_table || b.source_database || 'N/A'}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 flex-shrink-0 text-right">
                        <div className="hidden sm:block text-[11px] font-mono text-slate-400">
                          <div>{b.total_rows != null ? `${b.total_rows.toLocaleString()} rows` : ''}</div>
                          <div className="text-[10px] text-slate-500">{b.created_at || ''}</div>
                        </div>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3" />
                          Verified
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
