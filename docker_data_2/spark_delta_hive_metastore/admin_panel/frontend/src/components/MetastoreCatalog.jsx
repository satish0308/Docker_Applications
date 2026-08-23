import React, { useState, useEffect } from 'react';
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
  Calendar
} from 'lucide-react';

export default function MetastoreCatalog() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  // Inspector state
  const [activeTab, setActiveTab] = useState('grid'); // 'grid', 'schema', 'sql'
  const [rowLimit, setRowLimit] = useState(25);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectData, setInspectData] = useState(null);
  const [inspectError, setInspectError] = useState(null);

  // Custom SQL state
  const [customSql, setCustomSql] = useState('');
  const [sqlLoading, setSqlLoading] = useState(false);
  const [sqlResult, setSqlResult] = useState(null);

  const fetchTables = async () => {
    setLoading(true);
    try {
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

  const handleRunCustomSql = async () => {
    if (!customSql.trim() || !selectedTable) return;
    setSqlLoading(true);
    setSqlResult(null);
    const fullTbl = `${selectedTable.database_name}.${selectedTable.table_name}`;
    try {
      const res = await fetch('/api/metastore/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: fullTbl,
          custom_sql: customSql
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

  const filtered = tables.filter(t => 
    (t.table_name || '').toLowerCase().includes(search.toLowerCase()) || 
    (t.database_name || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-purple-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-400" />
            Hive Metastore Database & Catalog Explorer
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Browse databases, inspect schemas, query partition distributions, and load interactive live data grids with instant CSV export.
          </p>
        </div>

        <button
          onClick={fetchTables}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loading ? 'animate-spin' : ''}`} />
          Refresh Catalog
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: TABLES LIST */}
        <div className="lg:col-span-4 glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Registered Tables ({tables.length})</h3>
          </div>

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

          <div className="space-y-2 max-h-[600px] overflow-y-auto custom-scrollbar">
            {filtered.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/60 rounded-xl border border-white/5">
                No matching tables found.
              </div>
            ) : (
              filtered.map((t, idx) => {
                const isSelected = selectedTable?.table_name === t.table_name && selectedTable?.database_name === t.database_name;
                const isDelta = t.format === 'Delta Lake';

                return (
                  <div
                    key={idx}
                    onClick={() => handleSelectTable(t)}
                    className={`p-3 rounded-xl border transition cursor-pointer space-y-1.5 ${
                      isSelected 
                        ? 'bg-purple-950/40 border-purple-500 text-white shadow-md shadow-purple-500/10' 
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

        {/* RIGHT COLUMN: INSPECTOR TABS & DATA GRID */}
        <div className="lg:col-span-8 space-y-5">
          
          {selectedTable ? (
            <div className="glass-card p-6 space-y-6">
              
              {/* Selected Table Metadata Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-950/80 border border-white/10">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-extrabold text-white">{selectedTable.database_name}.{selectedTable.table_name}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold border border-purple-500/30">
                      {selectedTable.format}
                    </span>
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
                      Schema
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

              {/* TAB 1: DATA GRID */}
              {activeTab === 'grid' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-semibold text-slate-400">Rows to Sample:</span>
                      <select
                        value={rowLimit}
                        onChange={(e) => {
                          const lim = e.target.value;
                          setRowLimit(lim);
                          loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, lim);
                        }}
                        className="bg-slate-900 border border-white/15 rounded-lg px-2.5 py-1 text-xs font-bold text-white focus:outline-none focus:border-purple-500"
                      >
                        <option value={10}>10 Rows</option>
                        <option value={25}>25 Rows</option>
                        <option value={50}>50 Rows</option>
                        <option value={100}>100 Rows</option>
                        <option value={250}>250 Rows</option>
                      </select>
                      <button
                        onClick={() => loadTableData(`${selectedTable.database_name}.${selectedTable.table_name}`, rowLimit)}
                        className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                        title="Reload Data"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${inspectLoading ? 'animate-spin' : ''}`} />
                      </button>
                    </div>

                    <button
                      onClick={handleExportCsv}
                      disabled={!inspectData?.records || inspectData.records.length === 0}
                      className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-1.5 transition disabled:opacity-40"
                    >
                      <Download className="w-3.5 h-3.5 text-purple-400" />
                      Export CSV
                    </button>
                  </div>

                  {inspectLoading && (
                    <div className="p-12 flex flex-col items-center justify-center gap-2 text-xs text-purple-400 font-semibold bg-slate-950/40 rounded-xl border border-white/5">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Loading records from distributed Spark cluster...
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
                                <th key={col} className="p-2.5 font-bold text-slate-200 whitespace-nowrap">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5 text-slate-300">
                            {inspectData.records.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-white/[0.02]">
                                {Object.values(row).map((val, cIdx) => (
                                  <td key={cIdx} className="p-2.5 whitespace-nowrap max-w-xs truncate">
                                    {val == null ? <span className="text-slate-600">null</span> : String(val)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between px-1">
                        <span>Loaded {inspectData.records.length} sample rows (Total: {inspectData.total_rows?.toLocaleString()} rows)</span>
                        <span>Query Time: {inspectData.elapsed_sec}s</span>
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
                              <td className="p-3 text-purple-400">{col["Data Type"]}</td>
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
                    onClick={handleRunCustomSql}
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

    </div>
  );
}
