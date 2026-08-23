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
  FileJson,
  ChevronRight,
  ChevronDown,
  List,
  FolderTree,
  RotateCcw,
  Zap
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
  
  // View mode for tables list: 'tree' (grouped by db) or 'compact' (flat list)
  const [viewMode, setViewMode] = useState('tree');
  const [collapsedDbs, setCollapsedDbs] = useState({});

  // On-Demand Inspector State (No auto-query on table click)
  const [activeTab, setActiveTab] = useState('grid'); // 'grid', 'schema', 'sql'
  const [rowLimit, setRowLimit] = useState(25);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectData, setInspectData] = useState(null);
  const [inspectError, setInspectError] = useState(null);
  const [hasLoadedForTable, setHasLoadedForTable] = useState(null);

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
        setSelectedTable(tbls[0]);
        setCustomSql(`SELECT * FROM ${tbls[0].database_name}.${tbls[0].table_name} LIMIT 25;`);
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

  const handleSelectTable = (table, autoLoad = false) => {
    setSelectedTable(table);
    setGridSearch('');
    setSortCol(null);
    const fullTbl = `${table.database_name}.${table.table_name}`;
    setCustomSql(`SELECT * FROM ${fullTbl} LIMIT 25;`);
    
    // Clear previous inspection data if switching table, unless autoLoad requested
    if (hasLoadedForTable !== fullTbl) {
      setInspectData(null);
      setInspectError(null);
      setSqlResult(null);
    }

    if (autoLoad) {
      loadTableData(fullTbl, rowLimit);
    }
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
      setHasLoadedForTable(fullTbl);
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

  // Group tables by database for tree view
  const tablesByDb = useMemo(() => {
    const grouped = {};
    for (const t of filteredTables) {
      const db = t.database_name || 'default';
      if (!grouped[db]) grouped[db] = [];
      grouped[db].push(t);
    }
    return grouped;
  }, [filteredTables]);

  const toggleDbCollapse = (dbName) => {
    setCollapsedDbs(prev => ({
      ...prev,
      [dbName]: !prev[dbName]
    }));
  };

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
            Browse databases, inspect schemas, query partition distributions, and load interactive live data grids on-demand.
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
        
        {/* LEFT COLUMN: DE-CONGESTED FILTER CONTROLS & TABLES BROWSER */}
        <div className="lg:col-span-4 glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <TableIcon className="w-4 h-4 text-purple-400" />
              Registered Tables ({filteredTables.length}/{tables.length})
            </h3>

            {/* View Mode Toggle: Tree vs Compact */}
            <div className="flex items-center p-0.5 rounded-lg bg-slate-900 border border-white/10 text-xs">
              <button
                onClick={() => setViewMode('tree')}
                className={`p-1 rounded transition ${viewMode === 'tree' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                title="Database Tree View"
              >
                <FolderTree className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('compact')}
                className={`p-1 rounded transition ${viewMode === 'compact' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                title="Compact Flat List View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search tables or databases..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedDb}
                onChange={(e) => setSelectedDb(e.target.value)}
                className="w-1/2 bg-slate-900 border border-white/10 rounded-lg px-2 py-1 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-purple-500"
              >
                <option value="ALL">All Databases</option>
                {databases.map(d => (
                  <option key={d.name} value={d.name}>{d.name}</option>
                ))}
              </select>

              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="w-1/2 bg-slate-900 border border-white/10 rounded-lg px-2 py-1 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-purple-500"
              >
                <option value="ALL">All Formats</option>
                <option value="DELTA">⚡ Delta Lake</option>
                <option value="PARQUET">📦 Parquet / Ext</option>
              </select>
            </div>
          </div>

          {/* MODE 1: DATABASE TREE VIEW */}
          {viewMode === 'tree' && (
            <div className="space-y-3 max-h-[620px] overflow-y-auto custom-scrollbar">
              {Object.keys(tablesByDb).length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
                  No matching tables found.
                </div>
              ) : (
                Object.entries(tablesByDb).map(([dbName, dbTables]) => {
                  const isCollapsed = collapsedDbs[dbName];
                  return (
                    <div key={dbName} className="rounded-xl bg-slate-950/60 border border-white/10 overflow-hidden">
                      {/* Database Header Accordion */}
                      <button
                        onClick={() => toggleDbCollapse(dbName)}
                        className="w-full px-3 py-2 bg-slate-900/80 hover:bg-slate-900 flex items-center justify-between text-xs font-bold text-slate-200 border-b border-white/5"
                      >
                        <div className="flex items-center gap-2">
                          <Database className="w-3.5 h-3.5 text-purple-400" />
                          <span>{dbName}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-normal bg-purple-500/10 text-purple-300 border border-purple-500/20">
                            {dbTables.length} tables
                          </span>
                        </div>
                        {isCollapsed ? <ChevronRight className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
                      </button>

                      {/* Tables within Database */}
                      {!isCollapsed && (
                        <div className="p-1.5 space-y-1">
                          {dbTables.map((t, idx) => {
                            const isSelected = selectedTable?.table_name === t.table_name && selectedTable?.database_name === t.database_name;
                            const isDelta = t.format === 'Delta Lake';

                            return (
                              <div
                                key={idx}
                                onClick={() => handleSelectTable(t, false)}
                                className={`px-2.5 py-1.5 rounded-lg border transition cursor-pointer flex items-center justify-between gap-2 ${
                                  isSelected 
                                    ? 'bg-purple-950/60 border-purple-500 text-white shadow-sm' 
                                    : 'bg-slate-900/40 border-transparent hover:border-white/10 text-slate-300 hover:bg-slate-900'
                                }`}
                              >
                                <div className="flex items-center gap-2 truncate">
                                  <TableIcon className={`w-3 h-3 flex-shrink-0 ${isSelected ? 'text-purple-400' : 'text-slate-500'}`} />
                                  <span className="text-xs font-semibold truncate">{t.table_name}</span>
                                </div>

                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                    isDelta 
                                      ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30' 
                                      : 'bg-slate-800 text-slate-400 border border-white/10'
                                  }`}>
                                    {isDelta ? 'Delta' : 'Parquet'}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* MODE 2: COMPACT FLAT LIST VIEW */}
          {viewMode === 'compact' && (
            <div className="space-y-1.5 max-h-[620px] overflow-y-auto custom-scrollbar">
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
                      onClick={() => handleSelectTable(t, false)}
                      className={`px-3 py-2 rounded-xl border transition cursor-pointer flex items-center justify-between gap-2 ${
                        isSelected 
                          ? 'bg-purple-950/60 border-purple-500 text-white shadow-sm' 
                          : 'bg-slate-900/60 border-white/5 hover:border-white/20 text-slate-300'
                      }`}
                    >
                      <div className="truncate space-y-0.5">
                        <div className="font-bold text-xs text-white truncate flex items-center gap-1.5">
                          <TableIcon className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
                          <span>{t.database_name}.{t.table_name}</span>
                        </div>
                      </div>

                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold border flex-shrink-0 ${
                        isDelta 
                          ? 'bg-sky-500/10 border-sky-500/30 text-sky-400' 
                          : 'bg-slate-800 border-white/10 text-slate-400'
                      }`}>
                        {isDelta ? 'Delta Lake' : 'Parquet'}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          )}

        </div>

        {/* RIGHT COLUMN: ON-DEMAND INSPECTOR & DATA ENGINE */}
        <div className="lg:col-span-8 space-y-5">
          
          {selectedTable ? (
            <div className="glass-card p-6 space-y-6">
              
              {/* Selected Table Header Card */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-950/80 border border-white/10">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-black text-white">{selectedTable.database_name}.{selectedTable.table_name}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold border border-purple-500/30">
                      {selectedTable.format}
                    </span>
                    {inspectData?.total_rows != null && (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[10px] font-mono border border-emerald-500/30">
                        {inspectData.total_rows.toLocaleString()} rows
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-slate-400 truncate max-w-xl">
                    Location: <span className="text-slate-300">{selectedTable.storage_location || 'Managed Table'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Tab Selector */}
                  <div className="flex items-center p-1 rounded-lg bg-slate-900 border border-white/10">
                    <button
                      onClick={() => setActiveTab('grid')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'grid' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Data Grid
                    </button>
                    <button
                      onClick={() => setActiveTab('schema')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'schema' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Layers className="w-3.5 h-3.5" />
                      Schema ({inspectData?.schema?.length || '?'})
                    </button>
                    <button
                      onClick={() => setActiveTab('sql')}
                      className={`px-3 py-1.5 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                        activeTab === 'sql' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Custom SQL
                    </button>
                  </div>
                </div>
              </div>

              {/* ON-DEMAND ACTION TRIGGER (Shown when data hasn't been loaded yet) */}
              {!inspectData && !inspectLoading && !inspectError && (
                <div className="p-8 rounded-2xl bg-gradient-to-br from-slate-950 to-slate-900 border border-white/10 text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mx-auto text-purple-400 shadow-inner">
                    <Zap className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-black text-white">
                      Table Selected: <code>{selectedTable.database_name}.{selectedTable.table_name}</code>
                    </h4>
                    <p className="text-xs text-slate-400 max-w-md mx-auto">
                      Click below to inspect the schema, calculate row statistics, and load live data records across the Spark cluster on-demand.
                    </p>
                  </div>

                  <div className="flex items-center justify-center gap-3 pt-2">
                    <button
                      onClick={() => loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, rowLimit)}
                      className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-purple-600/30 flex items-center gap-2 transition"
                    >
                      <Play className="w-4 h-4 fill-current" />
                      Inspect Schema & Load Data (Limit {rowLimit})
                    </button>
                  </div>
                </div>
              )}

              {/* LOADING INDICATOR */}
              {inspectLoading && (
                <div className="p-12 text-center space-y-3 bg-slate-950/40 rounded-2xl border border-white/10">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto" />
                  <div className="text-xs font-bold text-white">Inspecting Schema & Reading Table Data...</div>
                  <div className="text-[11px] text-slate-400 font-mono">Executing Spark distributed scan on {selectedTable.database_name}.{selectedTable.table_name}</div>
                </div>
              )}

              {/* ERROR ALERT */}
              {inspectError && !inspectLoading && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-2">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4" />
                    Failed to inspect table:
                  </div>
                  <div className="font-mono text-[11px] bg-black/40 p-2 rounded">{inspectError}</div>
                  <button
                    onClick={() => loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, rowLimit)}
                    className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px] flex items-center gap-1 transition"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Retry Inspection
                  </button>
                </div>
              )}

              {/* TAB 1: INTERACTIVE DATA GRID */}
              {activeTab === 'grid' && inspectData && !inspectLoading && (
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
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-1.5 transition"
                      >
                        <Download className="w-3 h-3 text-emerald-400" />
                        CSV Export
                      </button>
                      <button
                        onClick={handleExportJson}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-1.5 transition"
                      >
                        <FileJson className="w-3 h-3 text-sky-400" />
                        JSON
                      </button>
                    </div>
                  </div>

                  {/* Data Table */}
                  <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-950 max-h-[500px] overflow-x-auto overflow-y-auto custom-scrollbar">
                    {sortedGridRecords.length === 0 ? (
                      <div className="p-8 text-center text-xs text-slate-500">
                        No rows found matching current filters.
                      </div>
                    ) : (
                      <table className="w-full text-left text-xs font-mono whitespace-nowrap">
                        <thead className="bg-slate-900/90 sticky top-0 z-10 border-b border-white/10 text-slate-400 uppercase text-[10px]">
                          <tr>
                            <th className="p-2.5 text-slate-500 w-10">#</th>
                            {Object.keys(sortedGridRecords[0]).map(col => (
                              <th
                                key={col}
                                onClick={() => handleSort(col)}
                                className="p-2.5 cursor-pointer hover:bg-slate-800/80 transition"
                              >
                                <div className="flex items-center gap-1.5">
                                  <span>{col}</span>
                                  {sortCol === col ? (
                                    sortDir === 'asc' ? <ArrowUp className="w-3 h-3 text-purple-400" /> : <ArrowDown className="w-3 h-3 text-purple-400" />
                                  ) : (
                                    <ArrowUpDown className="w-2.5 h-2.5 opacity-40" />
                                  )}
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300">
                          {sortedGridRecords.map((row, idx) => (
                            <tr key={idx} className="hover:bg-white/[0.02]">
                              <td className="p-2.5 text-slate-500 text-[10px]">{idx + 1}</td>
                              {Object.values(row).map((val, cIdx) => (
                                <td key={cIdx} className="p-2.5 truncate max-w-xs">
                                  {val == null ? <span className="text-slate-600 italic">null</span> : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: VISUAL SCHEMA */}
              {activeTab === 'schema' && (
                <div className="space-y-4">
                  {inspectData?.schema ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {inspectData.schema.map((f, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-slate-950/60 border border-white/10 flex items-center justify-between"
                        >
                          <div className="space-y-0.5">
                            <div className="font-bold text-xs text-white font-mono">{f.name}</div>
                            <div className="text-[10px] text-slate-500 font-mono">Field index: #{idx + 1}</div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold border ${getTypeColor(f.type)}`}>
                            {f.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-white/10 space-y-3">
                      <Layers className="w-8 h-8 text-purple-400 mx-auto opacity-80" />
                      <div>Schema hasn't been loaded yet for this table.</div>
                      <button
                        onClick={() => loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, rowLimit)}
                        className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs"
                      >
                        Inspect Schema Now
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: CUSTOM SQL QUERY RUNNER */}
              {activeTab === 'sql' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-300">Spark SQL Editor</label>
                    <textarea
                      value={customSql}
                      onChange={(e) => setCustomSql(e.target.value)}
                      rows={4}
                      className="w-full bg-slate-950 border border-white/15 rounded-xl p-3 text-xs font-mono text-emerald-400 focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    {/* Quick Template Chips */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] font-bold text-slate-500 uppercase">Quick Query:</span>
                      <button
                        onClick={() => {
                          const q = `SELECT count(*) as total_rows FROM ${selectedTable.database_name}.${selectedTable.table_name};`;
                          setCustomSql(q);
                          handleRunCustomSql(q);
                        }}
                        className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 hover:bg-purple-900/40 border border-white/10 text-slate-300 hover:text-purple-300"
                      >
                        COUNT(*)
                      </button>
                      <button
                        onClick={() => {
                          const q = `DESCRIBE EXTENDED ${selectedTable.database_name}.${selectedTable.table_name};`;
                          setCustomSql(q);
                          handleRunCustomSql(q);
                        }}
                        className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 hover:bg-purple-900/40 border border-white/10 text-slate-300 hover:text-purple-300"
                      >
                        DESCRIBE EXTENDED
                      </button>
                    </div>

                    <button
                      onClick={() => handleRunCustomSql()}
                      disabled={sqlLoading}
                      className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs flex items-center gap-2 transition disabled:opacity-50"
                    >
                      {sqlLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                      Execute SQL Query
                    </button>
                  </div>

                  {sqlResult && (
                    <div className="space-y-2 pt-2">
                      {sqlResult.error ? (
                        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono">
                          {sqlResult.error}
                        </div>
                      ) : (
                        <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-950 max-h-[400px] overflow-auto custom-scrollbar">
                          <table className="w-full text-left text-xs font-mono whitespace-nowrap">
                            <thead className="bg-slate-900 border-b border-white/10 text-slate-400 uppercase text-[10px]">
                              <tr>
                                {Object.keys(sqlResult.records[0] || {}).map(k => (
                                  <th key={k} className="p-2.5">{k}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 text-slate-300">
                              {sqlResult.records.map((r, idx) => (
                                <tr key={idx} className="hover:bg-white/[0.02]">
                                  {Object.values(r).map((v, cIdx) => (
                                    <td key={cIdx} className="p-2.5 truncate max-w-xs">{String(v)}</td>
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
            <div className="glass-card p-12 text-center space-y-3">
              <TableIcon className="w-10 h-10 text-slate-600 mx-auto" />
              <div className="text-sm font-bold text-slate-400">Select a table from the catalog to inspect</div>
            </div>
          )}

        </div>

      </div>

      {/* CREATE DATABASE MODAL */}
      {showCreateDbModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card p-6 max-w-md w-full space-y-4 border border-purple-500/30 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-purple-400" />
              Create New Metastore Database
            </h3>
            
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Database Name</label>
              <input
                type="text"
                placeholder="e.g. staging, analytics, raw"
                value={newDbName}
                onChange={(e) => setNewDbName(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {createDbMsg && (
              <div className={`p-3 rounded-xl text-xs font-semibold ${
                createDbMsg.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
              }`}>
                {createDbMsg.text}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => { setShowCreateDbModal(false); setCreateDbMsg(null); }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateDatabase}
                disabled={createDbLoading || !newDbName.trim()}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold text-white flex items-center gap-1.5 disabled:opacity-50 shadow-lg shadow-purple-600/30"
              >
                {createDbLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Create Database
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
