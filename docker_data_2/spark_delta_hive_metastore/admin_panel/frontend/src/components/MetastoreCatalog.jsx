import React, { useState, useEffect } from 'react';
import { Database, Table as TableIcon, Layers, RefreshCw, Search, ExternalLink } from 'lucide-react';

export default function MetastoreCatalog() {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTables = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/metastore/tables');
      const data = await res.json();
      setTables(data.tables || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  const handleSelectTable = async (table) => {
    setSelectedTable(table);
    setTableDetails(null);
    try {
      const res = await fetch(`/api/metastore/table/${table.database_name}/${table.table_name}`);
      const data = await res.json();
      setTableDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = tables.filter(t => 
    t.table_name.toLowerCase().includes(search.toLowerCase()) || 
    t.database_name.toLowerCase().includes(search.toLowerCase())
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
            Real-time catalog viewer querying PostgreSQL Metastore schema, column data types, storage paths, and Delta Lake partitions.
          </p>
        </div>

        <button
          onClick={fetchTables}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-purple-400" />
          Refresh Catalog
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* TABLES LIST */}
        <div className="glass-card p-5 space-y-3">
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

          <div className="space-y-1.5 max-h-[500px] overflow-y-auto custom-scrollbar">
            {filtered.map((t, idx) => {
              const isSelected = selectedTable?.table_name === t.table_name && selectedTable?.database_name === t.database_name;
              return (
                <button
                  key={idx}
                  onClick={() => handleSelectTable(t)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    isSelected 
                      ? 'bg-purple-950/40 border-purple-500 text-white' 
                      : 'bg-slate-900/60 border-white/5 hover:border-white/20 text-slate-300'
                  }`}
                >
                  <div className="font-bold text-xs flex items-center gap-1.5">
                    <TableIcon className="w-3.5 h-3.5 text-purple-400" />
                    <span>{t.database_name}.{t.table_name}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 font-mono truncate">{t.storage_location || 'HDFS Standard'}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* TABLE SCHEMA & PARTITION DETAILS */}
        <div className="lg:col-span-2 glass-card p-6 space-y-4">
          {selectedTable ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/10">
                <div>
                  <h3 className="text-base font-extrabold text-white">
                    {selectedTable.database_name}.{selectedTable.table_name}
                  </h3>
                  <div className="text-xs text-slate-400 mt-0.5 font-mono">{selectedTable.storage_location}</div>
                </div>

                <a
                  href="http://localhost:8888"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 font-bold text-xs flex items-center gap-1.5 transition"
                >
                  Query in Hue Studio
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {/* Columns Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Column Schema Definitions</h4>
                <div className="bg-slate-950 rounded-xl border border-white/10 overflow-hidden">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] border-b border-white/10">
                      <tr>
                        <th className="p-2.5">#</th>
                        <th className="p-2.5">Column Name</th>
                        <th className="p-2.5">Data Type</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                      {tableDetails?.columns?.map((c, i) => (
                        <tr key={i} className="hover:bg-white/[0.02]">
                          <td className="p-2.5 text-slate-500">{i + 1}</td>
                          <td className="p-2.5 font-bold text-purple-300">{c.column_name}</td>
                          <td className="p-2.5 text-sky-400">{c.type_name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Partitions List */}
              {tableDetails?.partitions && tableDetails.partitions.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Registered Dynamic Partitions</h4>
                  <div className="flex items-center gap-2 flex-wrap">
                    {tableDetails.partitions.map((p, pi) => (
                      <span key={pi} className="px-2.5 py-1 rounded-lg bg-slate-900 border border-purple-500/30 text-[11px] font-mono text-purple-300">
                        {p.partition_name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs">
              <Database className="w-8 h-8 opacity-40 mb-2" />
              Select a table from the catalog list to inspect its columns and partition keys.
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
