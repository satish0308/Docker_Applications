import React, { useState, useEffect, useMemo } from 'react';
import { 
  Database, 
  Table as TableIcon, 
  Layers, 
  RefreshCw, 
  Search, 
  ExternalLink, 
  Download, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Code, 
  Eye, 
  HardDrive,
  FileSpreadsheet,
  Calendar,
  Filter,
  Plus,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Sparkles,
  FileJson
} from 'lucide-react';

export default function MetastoreCatalog() {
  const [tables, setTables] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [selectedDb, setSelectedDb] = useState('ALL');
  const [selectedFormat, setSelectedFormat] = useState('ALL');
  const [selectedTable, setSelectedTable] = useState(null);
  const [search, setSearch] = useState('');
  const [gridSearch, setGridSearch] = useState('');
  const [loading, setLoading] = useState(false);

  // Inspector state
  const [activeTab, setActiveTab] = useState('grid'); // 'grid', 'schema', 'sql'
  const [rowLimit, setRowLimit] = useState(25);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectData, setInspectData] = useState(null);
  const [inspectError, setInspectError] = useState(null);

  // Sorting state for data grid
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  // Custom SQL state
  const [customSql, setCustomSql] = useState('');
  const [sqlLoading, setSqlLoading] = useState(false);
  const [sqlResult, setSqlResult] = useState(null);

  // Create Database modal state
  const [showCreateDbModal, setShowCreateDbModal] = useState(false);
  const [newDbName, setNewDbName] = useState('');
  const [createDbLoading, setCreateDbLoading] = useState(false);
  const [createDbMsg, setCreateDbMsg] = useState(null);

  const fetchDatabases = async () => {
    try {
      const res = await fetch('/api/metastore/databases');
      const data = await res.json();
      setDatabases(data.databases || []);
    } catch (err) {
      console.error("Failed to load databases:", err);
    }
  };

  const fetchTables = async () => {
    setLoading(true);
    try {
      await fetchDatabases();
      const res = await fetch('/api/metastore/tables');
      const data = await res.json();
      const tbls = data.tables || [];
      setTables(tbls);
      if (tbls.length > 0 && !selectedTable) {
        handleSelectTable(tbls[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  const handleSelectTable = (table) => {
    setSelectedTable(table);
    setGridSearch('');
    setSortCol(null);
    const fullTbl = `${table.database_name}.${table.table_name}`;
    setCustomSql(`SELECT * FROM ${fullTbl} LIMIT 25;`);
    loadTableData(fullTbl, rowLimit);
  };

  const loadTableData = async (fullTbl, limit) => {
    setInspectLoading(true);
    setInspectError(null);
    try {
      const res = await fetch('/api/metastore/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: fullTbl,
          limit: parseInt(limit) || 25
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to inspect table");
      setInspectData(data);
    } catch (err) {
      setInspectError(err.message);
    } finally {
      setInspectLoading(false);
    }
  };

  const handleRunCustomSql = async (overrideSql) => {
    const query = overrideSql || customSql;
    if (!query.trim() || !selectedTable) return;
    setSqlLoading(true);
    setSqlResult(null);
    const fullTbl = `${selectedTable.database_name}.${selectedTable.table_name}`;
    try {
      const res = await fetch('/api/metastore/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: fullTbl,
          custom_sql: query
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Query failed");
      setSqlResult(data);
    } catch (err) {
      setSqlResult({ error: err.message });
    } finally {
      setSqlLoading(false);
    }
  };

  const handleCreateDatabase = async () => {
    if (!newDbName.trim()) return;
    setCreateDbLoading(true);
    setCreateDbMsg(null);
    try {
      const res = await fetch('/api/metastore/create-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ database_name: newDbName.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create database");
      setCreateDbMsg({ type: 'success', text: `Database '${newDbName}' created successfully!` });
      setNewDbName('');
      setTimeout(() => {
        setShowCreateDbModal(false);
        setCreateDbMsg(null);
        fetchTables();
      }, 1000);
    } catch (err) {
      setCreateDbMsg({ type: 'error', text: err.message });
    } finally {
      setCreateDbLoading(false);
    }
  };

  const handleExportCsv = () => {
    const records = inspectData?.records || [];
    if (records.length === 0) return;

    const headers = Object.keys(records[0]);
    const csvRows = [];
    csvRows.push(headers.join(','));

    for (const r of records) {
      const values = headers.map(h => {
        const val = r[h] == null ? '' : String(r[h]).replace(/"/g, '""');
        return `"${val}"`;
      });
      csvRows.push(values.join(','));
    }

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${selectedTable?.table_name || 'table'}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJson = () => {
    const records = inspectData?.records || [];
    if (records.length === 0) return;
    const blob = new Blob([JSON.stringify(records, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${selectedTable?.table_name || 'table'}_export.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getTypeColor = (typeStr) => {
    const t = (typeStr || '').toUpperCase();
    if (t.includes('INT') || t.includes('LONG') || t.includes('SHORT')) return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
    if (t.includes('STRING') || t.includes('VARCHAR') || t.includes('CHAR')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    if (t.includes('DOUBLE') || t.includes('FLOAT') || t.includes('DECIMAL')) return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
    if (t.includes('TIME') || t.includes('DATE')) return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    if (t.includes('BOOL')) return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    return 'bg-slate-800 text-slate-400 border-white/10';
  };

  // Filter tables by search, selected db, and format
  const filteredTables = useMemo(() => {
    return tables.filter(t => {
      const matchSearch = 
        (t.table_name || '').toLowerCase().includes(search.toLowerCase()) || 
        (t.database_name || '').toLowerCase().includes(search.toLowerCase());
      const matchDb = selectedDb === 'ALL' || t.database_name === selectedDb;
      const matchFormat = selectedFormat === 'ALL' || 
        (selectedFormat === 'DELTA' && t.format === 'Delta Lake') ||
        (selectedFormat === 'PARQUET' && t.format !== 'Delta Lake');
      return matchSearch && matchDb && matchFormat;
    });
  }, [tables, search, selectedDb, selectedFormat]);

  // Filter & sort data grid rows
  const sortedGridRecords = useMemo(() => {
    let recs = inspectData?.records || [];
    if (gridSearch.trim()) {
      const q = gridSearch.toLowerCase();
      recs = recs.filter(r => 
        Object.values(r).some(v => String(v || '').toLowerCase().includes(q))
      );
    }
    if (sortCol) {
      recs = [...recs].sort((a, b) => {
        const vA = a[sortCol];
        const vB = b[sortCol];
        if (vA == null) return 1;
        if (vB == null) return -1;
        if (typeof vA === 'number' && typeof vB === 'number') {
          return sortDir === 'asc' ? vA - vB : vB - vA;
        }
        return sortDir === 'asc' 
          ? String(vA).localeCompare(String(vB))
          : String(vB).localeCompare(String(vA));
      });
    }
    return recs;
  }, [inspectData, gridSearch, sortCol, sortDir]);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-purple-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-400" />
            Hive Metastore Database & Catalog Explorer
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Browse databases, inspect schemas, query partition distributions, and load interactive live data grids with instant CSV/JSON export.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateDbModal(true)}
            className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold flex items-center gap-1.5 transition shadow-lg shadow-purple-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            New Database
          </button>
          <button
            onClick={fetchTables}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: FILTER CONTROLS & TABLES LIST */}
        <div className="lg:col-span-4 glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Registered Tables ({filteredTables.length}/{tables.length})
            </h3>
          </div>

          {/* Quick Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search tables or databases..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedDb}
                onChange={(e) => setSelectedDb(e.target.value)}
                className="w-1/2 bg-slate-900 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-purple-500"
              >
                <option value="ALL">All Databases</option>
                {databases.map(d => (
                  <option key={d.name} value={d.name}>{d.name}</option>
                ))}
              </select>

              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="w-1/2 bg-slate-900 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-purple-500"
              >
                <option value="ALL">All Formats</option>
                <option value="DELTA">⚡ Delta Lake</option>
                <option value="PARQUET">📦 Parquet / Ext</option>
              </select>
            </div>
          </div>

          {/* Table Items */}
          <div className="space-y-2 max-h-[560px] overflow-y-auto custom-scrollbar">
            {filteredTables.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
                No matching tables found.
              </div>
            ) : (
              filteredTables.map((t, idx) => {
                const isSelected = selectedTable?.table_name === t.table_name && selectedTable?.database_name === t.database_name;
                const isDelta = t.format === 'Delta Lake';

                return (
                  <div
                    key={idx}
                    onClick={() => handleSelectTable(t)}
                    className={`p-3 rounded-xl border transition cursor-pointer space-y-1.5 ${
                      isSelected 
                        ? 'bg-purple-950/50 border-purple-500 text-white shadow-lg shadow-purple-500/20' 
                        : 'bg-slate-900/60 border-white/5 hover:border-white/20 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-extrabold text-xs text-white flex items-center gap-1.5 truncate">
                        <TableIcon className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
                        <span className="truncate">{t.database_name}.{t.table_name}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                        isDelta 
                          ? 'bg-sky-500/10 border-sky-500/30 text-sky-400' 
                          : 'bg-slate-800 border-white/10 text-slate-400'
                      }`}>
                        {t.format}
                      </span>
                    </div>

                    <div className="text-[10px] text-slate-500 font-mono truncate">
                      {t.storage_location || 'Managed Table'}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: INSPECTOR TABS & INTERACTIVE DATA GRID */}
        <div className="lg:col-span-8 space-y-5">
          
          {selectedTable ? (
            <div className="glass-card p-6 space-y-6">
              
              {/* Selected Table Header Card */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-950/80 border border-white/10">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-black text-white">{selectedTable.database_name}.{selectedTable.table_name}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold border border-purple-500/30">
                      {selectedTable.format}
                    </span>
                    {inspectData?.total_rows != null && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-white/10">
                        {inspectData.total_rows.toLocaleString()} rows
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-slate-400 truncate max-w-xl">
                    Location: <span className="text-slate-300">{selectedTable.storage_location || 's3a://warehouse/'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Tab Selector */}
                  <div className="flex items-center p-1 rounded-lg bg-slate-900 border border-white/10">
                    <button
                      onClick={() => setActiveTab('grid')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'grid' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Data Grid
                    </button>
                    <button
                      onClick={() => setActiveTab('schema')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'schema' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Layers className="w-3.5 h-3.5" />
                      Schema ({inspectData?.schema?.length || 0})
                    </button>
                    <button
                      onClick={() => setActiveTab('sql')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'sql' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Custom SQL
                    </button>
                  </div>
                </div>
              </div>

              {/* TAB 1: INTERACTIVE DATA GRID */}
              {activeTab === 'grid' && (
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="flex items-center gap-1.5 bg-slate-900 border border-white/10 rounded-lg px-2.5 py-1">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Sample:</span>
                        <select
                          value={rowLimit}
                          onChange={(e) => {
                            const lim = e.target.value;
                            setRowLimit(lim);
                            loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, lim);
                          }}
                          className="bg-transparent text-xs font-bold text-white focus:outline-none"
                        >
                          <option value={10} className="bg-slate-900">10 Rows</option>
                          <option value={25} className="bg-slate-900">25 Rows</option>
                          <option value={50} className="bg-slate-900">50 Rows</option>
                          <option value={100} className="bg-slate-900">100 Rows</option>
                          <option value={250} className="bg-slate-900">250 Rows</option>
                        </select>
                      </div>

                      <div className="relative">
                        <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-slate-500" />
                        <input
                          type="text"
                          placeholder="Filter rows..."
                          value={gridSearch}
                          onChange={(e) => setGridSearch(e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-lg pl-8 pr-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-purple-500 w-36"
                        />
                      </div>

                      <button
                        onClick={() => loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, rowLimit)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                        title="Reload Data"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${inspectLoading ? 'animate-spin' : ''}`} />
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleExportCsv}
                        disabled={!inspectData?.records || inspectData.records.length === 0}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-1.5 transition disabled:opacity-40"
                      >
                        <Download className="w-3.5 h-3.5 text-purple-400" />
                        CSV
                      </button>
                      <button
                        onClick={handleExportJson}
                        disabled={!inspectData?.records || inspectData.records.length === 0}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-1.5 transition disabled:opacity-40"
                      >
                        <FileJson className="w-3.5 h-3.5 text-sky-400" />
                        JSON
                      </button>
                    </div>
                  </div>

                  {inspectLoading && (
                    <div className="p-12 flex flex-col items-center justify-center gap-2 text-xs text-purple-400 font-semibold bg-slate-950/40 rounded-xl border border-white/5">
                      <Loader2 className="w-6 h-6 animate-spin" />
                      Streaming records from distributed Spark cluster...
                    </div>
                  )}

                  {inspectError && (
                    <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs font-mono">
                      Error: {inspectError}
                    </div>
                  )}

                  {!inspectLoading && !inspectError && inspectData?.records && (
                    <div className="space-y-2">
                      <div className="max-h-96 overflow-x-auto overflow-y-auto border border-white/10 rounded-xl bg-slate-950 custom-scrollbar">
                        <table className="w-full text-left text-xs font-mono divide-y divide-white/5">
                          <thead className="bg-slate-900/90 sticky top-0 border-b border-white/10 text-slate-400">
                            <tr>
                              {Object.keys(inspectData.records[0] || {}).map((col) => (
                                <th 
                                  key={col} 
                                  onClick={() => handleSort(col)}
                                  className="p-2.5 font-bold text-slate-200 whitespace-nowrap cursor-pointer hover:text-purple-300 select-none"
                                >
                                  <div className="flex items-center gap-1.5">
                                    <span>{col}</span>
                                    {sortCol === col ? (
                                      sortDir === 'asc' ? <ArrowUp className="w-3 h-3 text-purple-400" /> : <ArrowDown className="w-3 h-3 text-purple-400" />
                                    ) : (
                                      <ArrowUpDown className="w-3 h-3 opacity-30" />
                                    )}
                                  </div>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5 text-slate-300">
                            {sortedGridRecords.length === 0 ? (
                              <tr>
                                <td colSpan={Object.keys(inspectData.records[0] || {}).length} className="p-6 text-center text-slate-500">
                                  No rows matching filter.
                                </td>
                              </tr>
                            ) : (
                              sortedGridRecords.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-white/[0.02]">
                                  {Object.values(row).map((val, cIdx) => (
                                    <td key={cIdx} className="p-2.5 whitespace-nowrap max-w-xs truncate">
                                      {val == null ? <span className="text-slate-600">null</span> : String(val)}
                                    </td>
                                  ))}
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>

                      <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between px-1">
                        <span>Showing {sortedGridRecords.length} rows (Total: {inspectData.total_rows?.toLocaleString()} rows)</span>
                        <span>Query Latency: {inspectData.elapsed_sec}s</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: VISUAL SCHEMA */}
              {activeTab === 'schema' && (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white">Visual Schema & Data Types</h4>
                  {inspectData?.schema ? (
                    <div className="border border-white/10 rounded-xl bg-slate-950 overflow-hidden">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-slate-900 border-b border-white/10 text-slate-400">
                          <tr>
                            <th className="p-3">#</th>
                            <th className="p-3">Column Name</th>
                            <th className="p-3">Data Type</th>
                            <th className="p-3">Nullable</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                          {inspectData.schema.map((col) => (
                            <tr key={col.Index} className="hover:bg-white/[0.02]">
                              <td className="p-3 text-slate-500">{col.Index}</td>
                              <td className="p-3 font-bold text-white">{col["Column Name"]}</td>
                              <td className="p-3">
                                <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold border ${getTypeColor(col["Data Type"])}`}>
                                  {col["Data Type"]}
                                </span>
                              </td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  col.Nullable === 'YES' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'
                                }`}>
                                  {col.Nullable}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-xs text-slate-500">Schema unavailable.</div>
                  )}
                </div>
              )}

              {/* TAB 3: CUSTOM SQL */}
              {activeTab === 'sql' && (
                <div className="space-y-4">
                  {/* Quick Query Chips */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Quick Templates:</span>
                    {[
                      { label: 'SELECT * LIMIT 50', sql: `SELECT * FROM ${selectedTable.database_name}.${selectedTable.table_name} LIMIT 50;` },
                      { label: 'COUNT(*)', sql: `SELECT COUNT(*) AS total_records FROM ${selectedTable.database_name}.${selectedTable.table_name};` },
                      { label: 'DESCRIBE EXTENDED', sql: `DESCRIBE EXTENDED ${selectedTable.database_name}.${selectedTable.table_name};` }
                    ].map((chip, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setCustomSql(chip.sql);
                          handleRunCustomSql(chip.sql);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/10 text-[11px] font-mono text-purple-300 transition"
                      >
                        {chip.label}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">Run Inline SQL Query</label>
                    <textarea
                      value={customSql}
                      onChange={(e) => setCustomSql(e.target.value)}
                      rows={4}
                      className="w-full bg-slate-950 border border-white/15 rounded-xl p-3 text-xs font-mono text-sky-300 focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  <button
                    onClick={() => handleRunCustomSql()}
                    disabled={sqlLoading}
                    className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-40"
                  >
                    {sqlLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                    Execute Inline Query
                  </button>

                  {sqlResult && (
                    <div className="space-y-2">
                      {sqlResult.error ? (
                        <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs font-mono">
                          {sqlResult.error}
                        </div>
                      ) : (
                        <div className="max-h-72 overflow-x-auto border border-white/10 rounded-xl bg-slate-950 custom-scrollbar">
                          <table className="w-full text-left text-xs font-mono divide-y divide-white/5">
                            <thead className="bg-slate-900 border-b border-white/10 text-slate-400">
                              <tr>
                                {Object.keys(sqlResult.records?.[0] || {}).map((col) => (
                                  <th key={col} className="p-2.5 font-bold text-slate-200 whitespace-nowrap">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                              {sqlResult.records?.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-white/[0.02]">
                                  {Object.values(row).map((val, cIdx) => (
                                    <td key={cIdx} className="p-2.5 whitespace-nowrap">
                                      {val == null ? 'null' : String(val)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

            </div>
          ) : (
            <div className="glass-card p-12 text-center text-xs text-slate-500">
              Select a table from the catalog list to inspect its contents.
            </div>
          )}

        </div>

      </div>

      {/* CREATE DATABASE MODAL */}
      {showCreateDbModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="glass-card max-w-md w-full p-6 space-y-4 border border-purple-500/30 shadow-2xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-purple-400" />
              Create Hive / Spark SQL Database
            </h3>
            
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Database Name:</label>
              <input
                type="text"
                value={newDbName}
                onChange={(e) => setNewDbName(e.target.value)}
                placeholder="e.g. analytics"
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {createDbMsg && (
              <div className={`p-3 rounded-xl text-xs font-bold ${
                createDbMsg.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
              }`}>
                {createDbMsg.text}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowCreateDbModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateDatabase}
                disabled={createDbLoading || !newDbName.trim()}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold text-white transition disabled:opacity-50"
              >
                {createDbLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Create Database'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
