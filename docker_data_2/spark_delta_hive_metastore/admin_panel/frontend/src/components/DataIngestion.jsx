import React, { useState, useEffect } from 'react';
import { 
  UploadCloud, 
  FileSpreadsheet, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Database, 
  Layers, 
  HardDrive, 
  Clock, 
  RefreshCw, 
  Eye, 
  Sliders,
  Folder,
  Server,
  Trash2,
  FileText,
  ChevronDown,
  ChevronUp,
  Sparkles,
  X,
  Plus
} from 'lucide-react';

export default function DataIngestion() {
  const [ingestionMode, setIngestionMode] = useState('server'); // 'server' or 'upload'
  
  // Server datasets state
  const [serverDatasets, setServerDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [availableColumns, setAvailableColumns] = useState([]);

  // File upload state
  const [file, setFile] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [schemaPreview, setSchemaPreview] = useState(null);

  // Common Ingestion Configuration
  const [databases, setDatabases] = useState(['default']);
  const [targetDb, setTargetDb] = useState('default');
  const [targetTable, setTargetTable] = useState('inventory_delta');
  const [format, setFormat] = useState('delta'); // 'delta' or 'parquet'
  const [writeMode, setWriteMode] = useState('overwrite'); // 'overwrite' or 'append'
  const [destStorage, setDestStorage] = useState('s3'); // 's3' or 'hdfs'
  const [chunkSize, setChunkSize] = useState(25);
  
  // Partition Columns (Multi-Select Array)
  const [selectedPartitions, setSelectedPartitions] = useState([]);
  const [isPartitionDropdownOpen, setIsPartitionDropdownOpen] = useState(false);
  const [customPartitionInput, setCustomPartitionInput] = useState('');

  // Execution & Job Registry
  const [submitting, setSubmitting] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [expandedJobId, setExpandedJobId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  const fetchDatabases = async () => {
    try {
      const res = await fetch('/api/metastore/databases');
      const data = await res.json();
      if (data.databases && data.databases.length > 0) {
        setDatabases(data.databases.map(d => d.name));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDatasetColumns = async (datasetName) => {
    if (!datasetName) return;
    try {
      const res = await fetch(`/api/ingestion/dataset-columns/${datasetName}`);
      const data = await res.json();
      const cols = data.columns || [];
      setAvailableColumns(cols);
      // Clean up any selected partitions that don't exist in the new dataset
      setSelectedPartitions(prev => prev.filter(col => cols.includes(col)));
    } catch (err) {
      console.error("Failed to load dataset columns:", err);
    }
  };

  const fetchServerDatasets = async () => {
    setDatasetsLoading(true);
    try {
      const res = await fetch('/api/ingestion/server-datasets');
      const data = await res.json();
      const ds = data.datasets || [];
      setServerDatasets(ds);
      if (ds.length > 0) {
        const initialDs = selectedDataset || ds[0].name;
        setSelectedDataset(initialDs);
        setTargetTable(initialDs.toLowerCase().replace(/[^a-z0-9_]/g, '_'));
        fetchDatasetColumns(initialDs);
      }
    } catch (err) {
      console.error("Failed to load server datasets:", err);
    } finally {
      setDatasetsLoading(false);
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch('/api/ingestion/jobs');
      const data = await res.json();
      const jobList = data.jobs || [];
      setJobs(jobList);
      if (jobList.length > 0 && !expandedJobId) {
        setExpandedJobId(jobList[0].job_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDatabases();
    fetchServerDatasets();
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDatasetChange = (name) => {
    setSelectedDataset(name);
    const cleanName = name.toLowerCase().replace(/[^a-z0-9_]/g, '_');
    setTargetTable(cleanName);
    setSelectedPartitions([]);
    fetchDatasetColumns(name);
  };

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setFile(selectedFile);
    setPreviewLoading(true);
    setSchemaPreview(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch('/api/ingestion/preview-schema', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to preview schema");
      setSchemaPreview(data);
      if (data.columns) {
        setAvailableColumns(data.columns);
      }
      
      const baseName = selectedFile.name.split('.')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_');
      setTargetTable(baseName);
    } catch (err) {
      console.error("Schema preview error:", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const togglePartitionCol = (col) => {
    if (selectedPartitions.includes(col)) {
      setSelectedPartitions(selectedPartitions.filter(c => c !== col));
    } else {
      setSelectedPartitions([...selectedPartitions, col]);
    }
  };

  const handleAddCustomPartition = () => {
    if (customPartitionInput.trim() && !selectedPartitions.includes(customPartitionInput.trim())) {
      setSelectedPartitions([...selectedPartitions, customPartitionInput.trim()]);
      setCustomPartitionInput('');
    }
  };

  const partitionColsStr = selectedPartitions.join(',');

  const handleSubmitServerDataset = async (e) => {
    e.preventDefault();
    if (!selectedDataset) return;
    setSubmitting(true);
    setFeedbackMsg(null);

    try {
      const res = await fetch('/api/ingestion/submit-server-dataset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_name: selectedDataset,
          target_database: targetDb,
          target_table: targetTable,
          table_format: format,
          write_mode: writeMode,
          dest_storage: destStorage,
          chunk_size: parseInt(chunkSize) || 100,
          partition_cols: partitionColsStr
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Submission failed");
      setFeedbackMsg({ type: 'success', text: `🚀 Chunked Ingestion launched: ${data.total_files} files in ${data.total_batches} batches!` });
      fetchJobs();
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setFeedbackMsg(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_database', targetDb);
    formData.append('target_table', targetTable);
    formData.append('table_format', format);
    formData.append('write_mode', writeMode);
    formData.append('dest_storage', destStorage);
    formData.append('partition_cols', partitionColsStr);

    try {
      const res = await fetch('/api/ingestion/submit', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Submission failed");
      setFeedbackMsg({ type: 'success', text: '🚀 Dataset uploaded and submitted to Spark cluster!' });
      fetchJobs();
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteJob = async (jobId) => {
    try {
      await fetch(`/api/ingestion/jobs/${jobId}`, { method: 'DELETE' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCancelJob = async (jobId) => {
    try {
      await fetch(`/api/ingestion/jobs/${jobId}/cancel`, { method: 'POST' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleClearCompleted = async () => {
    try {
      await fetch('/api/ingestion/jobs/clear-completed', { method: 'DELETE' });
      fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Module Banner */}
      <div className="glass-card p-6 border-l-4 border-l-sky-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-sky-400" />
            High-Throughput Chunked Ingestion & Lakehouse Loader
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Ingest terabyte-scale distributed datasets or upload local files. Automatically registers ACID Delta Lake and Hive tables on MinIO S3 and HDFS.
          </p>
        </div>

        <button
          onClick={() => { fetchServerDatasets(); fetchJobs(); }}
          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-semibold text-slate-200 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
          Refresh
        </button>
      </div>

      {feedbackMsg && (
        <div className={`p-4 rounded-xl text-xs font-bold border ${
          feedbackMsg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {feedbackMsg.text}
        </div>
      )}

      {/* INGESTION CONFIGURATION FORM */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: SOURCE SELECTION & PARAMETERS */}
        <div className="lg:col-span-6 glass-card p-6 space-y-5">
          
          {/* Mode Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-white/10">
            <button
              onClick={() => setIngestionMode('server')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                ingestionMode === 'server' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Folder className="w-4 h-4" />
              Pre-Staged Server Dataset (/data)
            </button>
            <button
              onClick={() => setIngestionMode('upload')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                ingestionMode === 'upload' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              Upload Local File
            </button>
          </div>

          {/* MODE A: SERVER DATASET PICKER */}
          {ingestionMode === 'server' && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300 flex items-center gap-2">
                  <Server className="w-4 h-4 text-sky-400" />
                  Select Pre-Staged Dataset in <code>/data/</code>:
                </label>
                {serverDatasets.length === 0 ? (
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-white/10 text-xs text-slate-400">
                    No folders found in <code>/data</code>.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-2">
                    {serverDatasets.map(ds => (
                      <div
                        key={ds.name}
                        onClick={() => handleDatasetChange(ds.name)}
                        className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between ${
                          selectedDataset === ds.name 
                            ? 'bg-sky-950/40 border-sky-500 text-white shadow-md shadow-sky-500/10' 
                            : 'bg-slate-900/60 border-white/5 hover:border-white/20 text-slate-300'
                        }`}
                      >
                        <div className="space-y-0.5">
                          <div className="font-bold text-xs text-white flex items-center gap-2">
                            <Folder className="w-3.5 h-3.5 text-sky-400" />
                            {ds.name}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            {ds.file_count} files ({ds.size_mb} MB)
                          </div>
                        </div>

                        <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-slate-800 border border-white/10 text-sky-300">
                          {ds.is_parquet ? 'Parquet' : 'Files'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Chunk Sizing Slider */}
              <div className="space-y-1.5 p-3 rounded-xl bg-slate-900/80 border border-white/10">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Micro-Batch Chunk Size:</span>
                  <span className="font-mono font-bold text-sky-400">{chunkSize} files / batch</span>
                </div>
                <input
                  type="range"
                  min="25"
                  max="200"
                  step="25"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(e.target.value)}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                />
                <div className="text-[10px] text-slate-400">
                  Batches large file trees iteratively to guarantee zero memory spikes and steady progress commits.
                </div>
              </div>
            </div>
          )}

          {/* MODE B: FILE UPLOAD */}
          {ingestionMode === 'upload' && (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-white/15 rounded-2xl p-6 text-center hover:border-sky-500/50 transition bg-slate-950/40">
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  onChange={handleFileChange}
                  accept=".csv,.parquet,.pq,.json"
                />
                <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
                  <UploadCloud className="w-8 h-8 text-sky-400" />
                  <span className="text-xs font-bold text-white">
                    {file ? file.name : "Click to select CSV, Parquet, or JSON dataset"}
                  </span>
                  <span className="text-[10px] text-slate-500">Supports .csv, .parquet, .json files</span>
                </label>
              </div>

              {previewLoading && (
                <div className="p-4 flex items-center justify-center gap-2 text-xs text-sky-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Detecting schema & column types...
                </div>
              )}
            </div>
          )}

          {/* TARGET TABLE & LAKEHOUSE DESTINATION CONFIG */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Target Database:</label>
              <select
                value={targetDb}
                onChange={(e) => setTargetDb(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
              >
                {databases.map(db => (
                  <option key={db} value={db}>{db}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Target Table Name:</label>
              <input
                type="text"
                value={targetTable}
                onChange={(e) => setTargetTable(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-sky-300 focus:outline-none focus:border-sky-500 font-bold"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Format:</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
              >
                <option value="delta">⚡ Delta Lake</option>
                <option value="parquet">📦 Parquet (Hive)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Write Mode:</label>
              <select
                value={writeMode}
                onChange={(e) => setWriteMode(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
              >
                <option value="overwrite">Overwrite (Replace)</option>
                <option value="append">Append</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Storage Tier:</label>
              <select
                value={destStorage}
                onChange={(e) => setDestStorage(e.target.value)}
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
              >
                <option value="s3">🪣 MinIO (S3 Object)</option>
                <option value="hdfs">📦 HDFS Warehouse</option>
              </select>
            </div>
          </div>

          {/* MULTI-SELECT PARTITION COLUMN DROPDOWN & BADGE SELECTOR */}
          <div className="space-y-2 relative">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-slate-400 uppercase flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-sky-400" />
                Partition Column(s) (Multi-Select):
              </label>
              <button
                type="button"
                onClick={() => setIsPartitionDropdownOpen(!isPartitionDropdownOpen)}
                className="text-[11px] text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1"
              >
                {isPartitionDropdownOpen ? 'Close Menu ▲' : 'Choose Columns ▼'}
              </button>
            </div>

            {/* Selected Partition Badges */}
            <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-xl bg-slate-900 border border-white/15 min-h-[42px]">
              {selectedPartitions.length === 0 ? (
                <span className="text-xs text-slate-500 italic">No partition columns selected (table will be unpartitioned)</span>
              ) : (
                selectedPartitions.map(col => (
                  <span
                    key={col}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/40 text-xs font-mono font-bold"
                  >
                    <span>{col}</span>
                    <button
                      type="button"
                      onClick={() => togglePartitionCol(col)}
                      className="hover:text-white transition"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))
              )}
            </div>

            {/* Multi-Select Dropdown Popover */}
            {isPartitionDropdownOpen && (
              <div className="p-3 rounded-xl bg-slate-950 border border-sky-500/40 shadow-2xl space-y-3 z-30 animate-in fade-in zoom-in duration-150">
                <div className="text-[11px] font-bold text-slate-400 uppercase">
                  Available Dataset Columns ({availableColumns.length}):
                </div>

                <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto custom-scrollbar">
                  {availableColumns.length === 0 ? (
                    <div className="text-xs text-slate-500 italic p-2">
                      Select a dataset above to inspect columns.
                    </div>
                  ) : (
                    availableColumns.map(col => {
                      const isSelected = selectedPartitions.includes(col);
                      return (
                        <button
                          key={col}
                          type="button"
                          onClick={() => togglePartitionCol(col)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-mono transition flex items-center gap-1.5 ${
                            isSelected
                              ? 'bg-sky-600 text-white font-bold shadow'
                              : 'bg-slate-900 border border-white/10 text-slate-300 hover:text-white hover:border-white/30'
                          }`}
                        >
                          <span>{isSelected ? '✓' : '+'}</span>
                          <span>{col}</span>
                        </button>
                      );
                    })
                  )}
                </div>

                {/* Custom Column Input */}
                <div className="flex items-center gap-2 pt-1 border-t border-white/10">
                  <input
                    type="text"
                    value={customPartitionInput}
                    onChange={(e) => setCustomPartitionInput(e.target.value)}
                    placeholder="Type custom column name..."
                    className="flex-1 bg-slate-900 border border-white/10 rounded-lg px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
                  />
                  <button
                    type="button"
                    onClick={handleAddCustomPartition}
                    className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-sky-300 border border-white/10"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </div>

          <button
            onClick={ingestionMode === 'server' ? handleSubmitServerDataset : handleSubmitUpload}
            disabled={submitting}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2 transition disabled:opacity-40"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            Execute Distributed Ingestion Pipeline
          </button>
        </div>

        {/* RIGHT COLUMN: PERSISTENT INGESTION JOBS & LIVE LOG STREAMER */}
        <div className="lg:col-span-6 glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Clock className="w-4 h-4 text-sky-400" />
              Persistent Ingestion Jobs ({jobs.length})
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={handleClearCompleted}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-bold border border-white/10 flex items-center gap-1 transition"
                title="Clear Completed and Interrupted Jobs"
              >
                <Trash2 className="w-3 h-3 text-slate-400" />
                Clear History
              </button>
              <button
                onClick={fetchJobs}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                title="Refresh Jobs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar">
            {jobs.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                No ingestion jobs launched yet. Select a dataset and execute.
              </div>
            ) : (
              jobs.map((job) => {
                const isExpanded = expandedJobId === job.job_id;
                const isSuccess = job.status === 'SUCCESS' || job.status === 'COMPLETED';
                const isRunning = job.status === 'RUNNING' || job.status === 'QUEUED';

                return (
                  <div
                    key={job.job_id}
                    className="p-4 rounded-xl bg-slate-950/80 border border-white/10 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-xs text-white">
                            {job.target_database || 'default'}.{job.target_table}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-slate-800 border border-white/10 text-slate-300">
                            {job.format}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          ID: {job.job_id} • {job.created_at || job.started_at}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border ${
                          isSuccess 
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : isRunning
                            ? 'bg-sky-500/10 text-sky-400 border-sky-500/30 animate-pulse'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}>
                          {job.status}
                        </span>

                        {isRunning && (
                          <button
                            onClick={() => handleCancelJob(job.job_id)}
                            className="px-2 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-[10px] font-bold border border-rose-500/30 transition"
                            title="Stop / Cancel Job"
                          >
                            Stop
                          </button>
                        )}

                        <button
                          onClick={() => setExpandedJobId(isExpanded ? null : job.job_id)}
                          className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                        >
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        <button
                          onClick={() => handleDeleteJob(job.job_id)}
                          className="p-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400"
                          title="Delete Job"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1">
                      <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            isSuccess ? 'bg-emerald-500' : isRunning ? 'bg-sky-500' : 'bg-rose-500'
                          }`}
                          style={{ width: `${job.progress_pct || 0}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                        <span className="truncate max-w-xs">{job.current_batch_msg || job.last_committed_msg || 'Executing...'}</span>
                        {job.total_rows && <span>{job.total_rows} rows ({job.elapsed_seconds})</span>}
                      </div>
                    </div>

                    {/* Logs Drawer */}
                    {isExpanded && job.recent_logs && (
                      <div className="p-3 rounded-lg bg-black/60 border border-white/5 font-mono text-[10px] text-slate-300 max-h-48 overflow-y-auto custom-scrollbar whitespace-pre-wrap">
                        {job.recent_logs}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
