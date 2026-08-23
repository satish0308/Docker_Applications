import React, { useState, useMemo } from 'react';
import { 
  Activity, 
  ExternalLink, 
  Server, 
  HardDrive, 
  Cpu, 
  Shield, 
  Globe, 
  Copy, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Search, 
  Filter,
  Terminal,
  Database,
  Layers,
  Sparkles,
  Play,
  RotateCcw
} from 'lucide-react';

export default function ClusterHealth({ services = [], onRefresh }) {
  const [search, setSearch] = useState('');
  const [selectedTier, setSelectedTier] = useState('ALL');
  const [copiedEndpoint, setCopiedEndpoint] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedEndpoint(id);
    setTimeout(() => setCopiedEndpoint(null), 2000);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    if (onRefresh) await onRefresh();
    setTimeout(() => setRefreshing(false), 600);
  };

  // Comprehensive Catalog of all BDP Cluster Endpoints, Protocols & Portals
  const clusterEndpoints = useMemo(() => [
    // --- Interactive Studios & Portals ---
    {
      id: 'hue',
      name: 'Hue Analytics Web Studio',
      tier: 'Interactive Studios',
      serviceKey: 'hue',
      container: 'hue',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8888,
      externalPort: 8888,
      url: 'http://localhost:8888',
      desc: 'Interactive Web SQL Editor, Hive Metastore & Table Explorer',
      icon: '🎨',
      isPortal: true
    },
    {
      id: 'jupyter',
      name: 'JupyterLab Data Science',
      tier: 'Interactive Studios',
      serviceKey: 'jupyter',
      container: 'jupyter-notebook',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8888,
      externalPort: 8889,
      url: 'http://localhost:8889',
      desc: 'Interactive PySpark, Delta Lake & Lakehouse Notebooks',
      icon: '📓',
      isPortal: true
    },
    {
      id: 'minio_console',
      name: 'MinIO S3 Storage Console',
      tier: 'Storage & Object Store',
      serviceKey: 'minio',
      container: 'minio',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 9001,
      externalPort: 9001,
      url: 'http://localhost:9001',
      desc: 'S3 Buckets, Access Keys & Delta Lake Object Browser',
      icon: '🪣',
      isPortal: true
    },
    {
      id: 'spark_master_ui',
      name: 'Spark Master Web UI',
      tier: 'Compute Engines',
      serviceKey: 'spark',
      container: 'spark',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8080,
      externalPort: 8089,
      url: 'http://localhost:8089',
      desc: 'Cluster Overview, Worker Nodes & Active Driver Applications',
      icon: '⚡',
      isPortal: true
    },
    {
      id: 'spark_history_ui',
      name: 'Spark History Server',
      tier: 'Compute Engines',
      serviceKey: 'spark',
      container: 'spark',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 18080,
      externalPort: 18080,
      url: 'http://localhost:18080',
      desc: 'Completed DAG Stages, Task Metrics & Event Log Playback',
      icon: '📜',
      isPortal: true
    },
    {
      id: 'spark_driver_ui',
      name: 'Spark Active Application UI',
      tier: 'Compute Engines',
      serviceKey: 'spark',
      container: 'spark',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 4040,
      externalPort: 4040,
      url: 'http://localhost:4040',
      desc: 'Active SparkContext Execution Stages, Storage & DAG Details',
      icon: '🔥',
      isPortal: true
    },
    {
      id: 'namenode_ui',
      name: 'Hadoop HDFS NameNode UI',
      tier: 'Storage & Object Store',
      serviceKey: 'namenode',
      container: 'namenode',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 9870,
      externalPort: 9870,
      url: 'http://localhost:9870',
      desc: 'Distributed File System Explorer & Storage Block Health',
      icon: '📦',
      isPortal: true
    },
    {
      id: 'datanode_ui',
      name: 'Hadoop HDFS DataNode UI',
      tier: 'Storage & Object Store',
      serviceKey: 'datanode',
      container: 'datanode',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 9864,
      externalPort: 9864,
      url: 'http://localhost:9864',
      desc: 'HDFS Block Storage Node Diagnostics & Volume Utilization',
      icon: '🗄️',
      isPortal: true
    },
    {
      id: 'yarn_rm_ui',
      name: 'YARN ResourceManager UI',
      tier: 'Compute Engines',
      serviceKey: 'resourcemanager',
      container: 'resourcemanager',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8088,
      externalPort: 8088,
      url: 'http://localhost:8088',
      desc: 'Distributed Memory Pool & YARN Application Queue Manager',
      icon: '🐘',
      isPortal: true
    },
    {
      id: 'yarn_nm_ui',
      name: 'YARN NodeManager UI',
      tier: 'Compute Engines',
      serviceKey: 'nodemanager',
      container: 'nodemanager',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8042,
      externalPort: 8042,
      url: 'http://localhost:8042',
      desc: 'YARN Container Execution Daemon Node Diagnostics',
      icon: '⚙️',
      isPortal: true
    },
    {
      id: 'pgadmin_ui',
      name: 'pgAdmin 4 Database Console',
      tier: 'Security & Management',
      serviceKey: 'pgadmin',
      container: 'pgadmin',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 80,
      externalPort: 8081,
      url: 'http://localhost:8081',
      desc: 'Web-based GUI for PostgreSQL Metastore Database',
      icon: '🛠️',
      isPortal: true
    },
    {
      id: 'keycloak_ui',
      name: 'Keycloak IAM & SSO Console',
      tier: 'Security & Management',
      serviceKey: 'keycloak',
      container: 'keycloak',
      type: 'Web UI',
      protocol: 'HTTP',
      internalPort: 8080,
      externalPort: 8080,
      url: 'http://localhost:8080',
      desc: 'Identity Provider & OAuth2 Lakehouse Security Gateway',
      icon: '🔐',
      isPortal: true
    },
    {
      id: 'admin_panel_ui',
      name: 'BDP Control Center & API',
      tier: 'Security & Management',
      serviceKey: 'admin-panel',
      container: 'admin-panel',
      type: 'Control Center / API',
      protocol: 'HTTP / REST',
      internalPort: 8501,
      externalPort: 8501,
      url: 'http://localhost:8501',
      desc: 'Central Management Web UI, Ingestion Pipelines & REST Engine',
      icon: '🎛️',
      isPortal: true
    },

    // --- Service Protocols & Client Endpoints ---
    {
      id: 'spark_master_rpc',
      name: 'Spark Master Cluster RPC',
      tier: 'Compute Engines',
      serviceKey: 'spark',
      container: 'spark',
      type: 'Cluster RPC',
      protocol: 'Spark RPC',
      internalPort: 7077,
      externalPort: 7077,
      url: 'spark://spark:7077',
      desc: 'Spark Master URL for spark-submit & distributed driver jobs',
      icon: '⚡',
      isPortal: false
    },
    {
      id: 'minio_s3_api',
      name: 'MinIO S3 Storage API',
      tier: 'Storage & Object Store',
      serviceKey: 'minio',
      container: 'minio',
      type: 'Storage API',
      protocol: 'S3A / HTTP',
      internalPort: 9000,
      externalPort: 9000,
      url: 'http://localhost:9000',
      desc: 'S3-compatible Object Storage Endpoint for PySpark & Delta Lake (s3a://)',
      icon: '🪣',
      isPortal: false
    },
    {
      id: 'spark_thrift',
      name: 'Spark Thrift Server (JDBC/ODBC)',
      tier: 'Compute Engines',
      serviceKey: 'spark-thriftserver',
      container: 'spark-thriftserver',
      type: 'BI Gateway',
      protocol: 'JDBC / Thrift',
      internalPort: 10000,
      externalPort: 10000,
      url: 'jdbc:hive2://localhost:10000/default',
      desc: 'JDBC/ODBC gateway for PowerBI, Tableau, and DBeaver into SparkSQL',
      icon: '📊',
      isPortal: false
    },
    {
      id: 'livy_rest',
      name: 'Apache Livy REST Gateway',
      tier: 'Compute Engines',
      serviceKey: 'livy',
      container: 'livy',
      type: 'REST API',
      protocol: 'HTTP / REST',
      internalPort: 8998,
      externalPort: 8998,
      url: 'http://localhost:8998',
      desc: 'REST API endpoint for submitting interactive Spark jobs and sessions',
      icon: '🔌',
      isPortal: false
    },
    {
      id: 'hdfs_rpc',
      name: 'HDFS Distributed IPC RPC',
      tier: 'Storage & Object Store',
      serviceKey: 'namenode',
      container: 'namenode',
      type: 'Storage Protocol',
      protocol: 'HDFS IPC',
      internalPort: 9000,
      externalPort: 9000,
      url: 'hdfs://namenode:9000',
      desc: 'HDFS distributed namespace and warehouse storage URI (hdfs://)',
      icon: '📦',
      isPortal: false
    },
    {
      id: 'postgres_db',
      name: 'PostgreSQL Hive Metastore DB',
      tier: 'Storage & Object Store',
      serviceKey: 'postgres',
      container: 'hive-metastore-postgres',
      type: 'Database',
      protocol: 'PostgreSQL JDBC',
      internalPort: 5432,
      externalPort: 5432,
      url: 'postgresql://postgres:postgres@localhost:5432/metastore',
      desc: 'Relational database backend powering Hive Metastore and Hue sessions',
      icon: '🐘',
      isPortal: false
    },
    {
      id: 'hive_metastore_thrift',
      name: 'Hive Metastore Thrift Service',
      tier: 'Storage & Object Store',
      serviceKey: 'hive',
      container: 'hive-server',
      type: 'Catalog Thrift',
      protocol: 'Thrift RPC',
      internalPort: 9083,
      externalPort: 9083,
      url: 'thrift://hive-server:9083',
      desc: 'Central Hive Metastore Thrift protocol endpoint for schema cataloging',
      icon: '🐝',
      isPortal: false
    },
    {
      id: 'spark_worker_nodes',
      name: 'Spark Worker Fleet (1–8 Nodes)',
      tier: 'Compute Engines',
      serviceKey: 'spark-worker',
      container: 'spark_delta_hive_metastore-spark-worker-1',
      type: 'Worker Web UIs',
      protocol: 'HTTP',
      internalPort: 8081,
      externalPort: '8091–8098',
      url: 'http://localhost:8091',
      desc: 'Distributed Spark Executor nodes managing cached memory and tasks',
      icon: '⚙️',
      isPortal: false
    }
  ], []);

  // Map service health status
  const serviceStatusMap = useMemo(() => {
    const map = {};
    for (const s of services) {
      map[s.key || s.id || s.service_key] = s;
      if (s.name) map[s.name.toLowerCase()] = s;
      if (s.container_name) map[s.container_name] = s;
    }
    return map;
  }, [services]);

  const getServiceStatus = (endpoint) => {
    const s = serviceStatusMap[endpoint.serviceKey] || serviceStatusMap[endpoint.container];
    if (s) {
      return s.status === 'RUNNING' || s.status === 'HEALTHY' ? 'RUNNING' : 'STOPPED';
    }
    return 'UNKNOWN';
  };

  // Filter endpoints
  const filteredEndpoints = useMemo(() => {
    return clusterEndpoints.filter(e => {
      const matchSearch = 
        e.name.toLowerCase().includes(search.toLowerCase()) ||
        e.desc.toLowerCase().includes(search.toLowerCase()) ||
        e.protocol.toLowerCase().includes(search.toLowerCase()) ||
        String(e.externalPort).includes(search);
      const matchTier = selectedTier === 'ALL' || e.tier === selectedTier;
      return matchSearch && matchTier;
    });
  }, [clusterEndpoints, search, selectedTier]);

  const portalsList = useMemo(() => {
    return clusterEndpoints.filter(e => e.isPortal);
  }, [clusterEndpoints]);

  const tiers = ['ALL', 'Interactive Studios', 'Compute Engines', 'Storage & Object Store', 'Security & Management'];

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-emerald-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            BDP Cluster Infrastructure Health, Protocols & Direct Endpoints
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Complete topology of all 21 distributed lakehouse portals, cluster RPCs, storage gateways, and REST endpoints.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-bold text-slate-200 flex items-center gap-2 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Endpoints
          </button>
        </div>
      </div>

      {/* SECTION 1: INTERACTIVE WEB PORTALS (1-CLICK BROWSER LAUNCHERS) */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Globe className="w-4 h-4 text-emerald-400" />
          Interactive Web Portals & Consoles ({portalsList.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {portalsList.map((portal) => {
            const status = getServiceStatus(portal);
            const isOnline = status === 'RUNNING';

            return (
              <a
                key={portal.id}
                href={portal.url}
                target="_blank"
                rel="noreferrer"
                className="glass-card-sm p-4 border border-white/[0.08] hover:border-emerald-500/50 hover:bg-slate-900/90 transition group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-2xl">{portal.icon}</span>
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
                      <span className="text-[11px] font-mono font-bold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                        :{portal.externalPort}
                      </span>
                    </div>
                  </div>

                  <div className="font-bold text-xs text-white mt-3 group-hover:text-emerald-300 transition truncate">
                    {portal.name}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">{portal.desc}</div>
                </div>

                <div className="mt-4 pt-2.5 border-t border-white/5 flex items-center justify-between text-[11px] font-semibold text-slate-400 group-hover:text-white transition">
                  <span className="flex items-center gap-1 text-emerald-400 font-bold">
                    Open Web UI
                  </span>
                  <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-white" />
                </div>
              </a>
            );
          })}
        </div>
      </div>

      {/* SECTION 2: COMPREHENSIVE PROTOCOLS & ALL SERVICE ENDPOINTS TABLE */}
      <div className="glass-card p-6 space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wide text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-sky-400" />
              All Cluster Service Endpoints & Client Protocols ({filteredEndpoints.length})
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Copy connection strings and connection URLs for JDBC, S3A, Thrift, Spark RPC, and REST clients.
            </p>
          </div>

          {/* Search & Tier Filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search endpoints, ports..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 w-48"
              />
            </div>

            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-300 focus:outline-none focus:border-emerald-500"
            >
              {tiers.map(t => (
                <option key={t} value={t}>{t === 'ALL' ? 'All Tiers' : t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Endpoints Table */}
        <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-950/80 overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-xs font-mono whitespace-nowrap">
            <thead className="bg-slate-900/90 border-b border-white/10 text-slate-400 uppercase text-[10px]">
              <tr>
                <th className="p-3">Service & Endpoint Name</th>
                <th className="p-3">Tier</th>
                <th className="p-3">Protocol</th>
                <th className="p-3">Port (Host : Container)</th>
                <th className="p-3">Connection String / URL</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {filteredEndpoints.map((ep) => {
                const status = getServiceStatus(ep);
                const isOnline = status === 'RUNNING';
                const isCopied = copiedEndpoint === ep.id;

                return (
                  <tr key={ep.id} className="hover:bg-white/[0.02] transition">
                    <td className="p-3">
                      <div className="flex items-center gap-2.5">
                        <span className="text-lg">{ep.icon}</span>
                        <div>
                          <div className="font-bold text-xs text-white flex items-center gap-1.5">
                            <span>{ep.name}</span>
                            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-rose-500'}`} />
                          </div>
                          <div className="text-[10px] text-slate-500 font-sans">{ep.desc}</div>
                        </div>
                      </div>
                    </td>

                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-slate-300 border border-white/10">
                        {ep.tier}
                      </span>
                    </td>

                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/10 text-purple-300 border border-purple-500/20">
                        {ep.protocol}
                      </span>
                    </td>

                    <td className="p-3">
                      <div className="font-bold text-white">
                        {ep.externalPort} <span className="text-slate-500 font-normal">: {ep.internalPort}</span>
                      </div>
                    </td>

                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <code className="text-emerald-400 bg-black/40 px-2 py-1 rounded text-[11px] border border-white/5 truncate max-w-sm">
                          {ep.url}
                        </code>
                        <button
                          onClick={() => copyToClipboard(ep.url, ep.id)}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                          title="Copy URL"
                        >
                          {isCopied ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </td>

                    <td className="p-3 text-right">
                      {ep.url.startsWith('http') ? (
                        <a
                          href={ep.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 text-[11px] font-bold border border-sky-500/30 transition"
                        >
                          <span>Open</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <button
                          onClick={() => copyToClipboard(ep.url, ep.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-bold border border-white/10 transition"
                        >
                          <span>{isCopied ? 'Copied!' : 'Copy URI'}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
