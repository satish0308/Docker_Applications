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
  EyeOff,
  Sliders,
  Folder,
  FolderOpen,
  Server,
  Trash2,
  FileText,
  ChevronDown,
  ChevronUp,
  Sparkles,
  X,
  Plus,
  Cloud,
  Key,
  Lock,
  Search,
  CheckSquare,
  Square,
  ArrowUp,
  Table as TableIcon,
  Globe,
  Radio
} from 'lucide-react';

export default function DataIngestion() {
  const [ingestionMode, setIngestionMode] = useState('server'); // 'server' | 's3_stream' | 'upload'
  
  // Server datasets state
  const [serverDatasets, setServerDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [availableColumns, setAvailableColumns] = useState([]);

  // AWS S3 Cloud Stream & File Explorer State
  const [s3AccessKey, setS3AccessKey] = useState(() => {
    const saved = localStorage.getItem('bdp_aws_s3_creds');
    return saved ? (JSON.parse(saved).accessKey || '') : '';
  });
  const [s3SecretKey, setS3SecretKey] = useState(() => {
    const saved = localStorage.getItem('bdp_aws_s3_creds');
    return saved ? (JSON.parse(saved).secretKey || '') : '';
  });
  const [s3Region, setS3Region] = useState(() => {
    const saved = localStorage.getItem('bdp_aws_s3_creds');
    return saved ? (JSON.parse(saved).region || 'us-east-1') : 'us-east-1';
  });
  const [s3Bucket, setS3Bucket] = useState(() => {
    const saved = localStorage.getItem('bdp_aws_s3_creds');
    return saved ? (JSON.parse(saved).bucket || '') : '';
  });
  const [s3Prefix, setS3Prefix] = useState('');
  const [s3ParentPrefix, setS3ParentPrefix] = useState('');
  const [s3BucketsList, setS3BucketsList] = useState([]);
  const [s3Folders, setS3Folders] = useState([]);
  const [s3Files, setS3Files] = useState([]);
  const [s3SelectedFiles, setS3SelectedFiles] = useState([]);
  const [s3Connecting, setS3Connecting] = useState(false);
  const [s3Connected, setS3Connected] = useState(false);
  const [s3Browsing, setS3Browsing] = useState(false);
  const [s3SearchTerm, setS3SearchTerm] = useState('');
  const [s3PreviewData, setS3PreviewData] = useState(null);
  const [s3PreviewLoading, setS3PreviewLoading] = useState(false);
  const [s3StreamMode, setS3StreamMode] = useState('batch'); // 'batch' | 'stream'
  const [showSecretKey, setShowSecretKey] = useState(false);
  const [isS3ConfigExpanded, setIsS3ConfigExpanded] = useState(true);

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

  const handleSaveS3Creds = (keyVal, secretVal, regionVal, bucketVal) => {
    localStorage.setItem('bdp_aws_s3_creds', JSON.stringify({
      accessKey: keyVal,
      secretKey: secretVal,
      region: regionVal,
      bucket: bucketVal
    }));
  };

  const handleTestS3Connection = async () => {
    if (!s3AccessKey || !s3SecretKey) {
      setFeedbackMsg({ type: 'error', text: 'Please enter AWS Access Key ID and Secret Access Key.' });
      return;
    }
    setS3Connecting(true);
    setFeedbackMsg(null);
    try {
      const res = await fetch('/api/ingestion/s3/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aws_access_key: s3AccessKey,
          aws_secret_key: s3SecretKey,
          aws_region: s3Region,
          bucket: s3Bucket || undefined
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Connection failed');
      setS3Connected(true);
      if (data.buckets) {
        setS3BucketsList(data.buckets);
        if (!s3Bucket && data.buckets.length > 0) {
          setS3Bucket(data.buckets[0]);
        }
      }
      handleSaveS3Creds(s3AccessKey, s3SecretKey, s3Region, s3Bucket);
      setFeedbackMsg({ type: 'success', text: `✅ ${data.message}` });
      if (s3Bucket || (data.buckets && data.buckets.length > 0)) {
        browseS3Folder(s3Bucket || data.buckets[0], s3Prefix);
      }
    } catch (err) {
      setS3Connected(false);
      setFeedbackMsg({ type: 'error', text: err.message });
    } finally {
      setS3Connecting(false);
    }
  };

  const browseS3Folder = async (targetBucket, targetPrefix = '') => {
    const bkt = targetBucket || s3Bucket;
    if (!s3AccessKey || !s3SecretKey || !bkt) return;
    setS3Browsing(true);
    try {
      const res = await fetch('/api/ingestion/s3/browse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aws_access_key: s3AccessKey,
          aws_secret_key: s3SecretKey,
          aws_region: s3Region,
          bucket: bkt,
          prefix: targetPrefix
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to browse S3 folder');
      setS3Folders(data.folders || []);
      setS3Files(data.files || []);
      setS3Prefix(data.current_prefix || '');
      setS3ParentPrefix(data.parent_prefix || '');
      setS3SelectedFiles([]); // Reset selection when moving folders
      setS3Connected(true);
      
      // Auto-suggest target table name from folder name
      const cleanPrefix = (data.current_prefix || '').replace(/\/$/, '');
      const lastFolder = cleanPrefix.split('/').pop() || bkt;
      if (lastFolder) {
        setTargetTable(lastFolder.toLowerCase().replace(/[^a-z0-9_]/g, '_'));
      }
    } catch (err) {
      console.error('S3 browse error:', err);
      setFeedbackMsg({ type: 'error', text: err.message });
    } finally {
      setS3Browsing(false);
    }
  };

  const handlePreviewS3File = async (key) => {
    if (!s3AccessKey || !s3SecretKey || !s3Bucket || !key) return;
    setS3PreviewLoading(true);
    setS3PreviewData(null);
    try {
      const res = await fetch('/api/ingestion/s3/preview-schema', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aws_access_key: s3AccessKey,
          aws_secret_key: s3SecretKey,
          aws_region: s3Region,
          bucket: s3Bucket,
          key: key
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to preview schema');
      setS3PreviewData(data);
      if (data.columns) {
        setAvailableColumns(data.columns);
      }
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: `S3 Preview Error: ${err.message}` });
    } finally {
      setS3PreviewLoading(false);
    }
  };

  const toggleSelectS3File = (fileKey) => {
    if (s3SelectedFiles.includes(fileKey)) {
      setS3SelectedFiles(s3SelectedFiles.filter(k => k !== fileKey));
    } else {
      setS3SelectedFiles([...s3SelectedFiles, fileKey]);
    }
  };

  const filteredS3Files = s3Files.filter(f => 
    !s3SearchTerm || f.name.toLowerCase().includes(s3SearchTerm.toLowerCase()) || f.key.toLowerCase().includes(s3SearchTerm.toLowerCase())
  );

  const toggleSelectAllS3Files = () => {
    if (s3SelectedFiles.length === filteredS3Files.length && filteredS3Files.length > 0) {
      setS3SelectedFiles([]);
    } else {
      setS3SelectedFiles(filteredS3Files.map(f => f.key));
    }
  };

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

  const handleSubmitS3Stream = async (e) => {
    e.preventDefault();
    if (!s3AccessKey || !s3SecretKey || !s3Bucket) {
      setFeedbackMsg({ type: 'error', text: 'AWS S3 Credentials and Bucket Name are required.' });
      return;
    }
    if (!targetTable) {
      setFeedbackMsg({ type: 'error', text: 'Target Table Name is required.' });
      return;
    }
    setSubmitting(true);
    setFeedbackMsg(null);

    try {
      const res = await fetch('/api/ingestion/s3/submit-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aws_access_key: s3AccessKey,
          aws_secret_key: s3SecretKey,
          aws_region: s3Region,
          bucket: s3Bucket,
          source_prefix: s3Prefix,
          selected_files: s3SelectedFiles,
          mode: s3StreamMode,
          target_database: targetDb,
          target_table: targetTable,
          table_format: format,
          write_mode: writeMode,
          dest_storage: destStorage,
          chunk_size: parseInt(chunkSize) || 50,
          partition_cols: partitionColsStr
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Submission failed');
      setFeedbackMsg({ type: 'success', text: `🚀 AWS S3 Cloud Stream initiated: Target Table \`${targetDb}.${targetTable}\` (${format.toUpperCase()})` });
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
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                ingestionMode === 'server' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Folder className="w-4 h-4" />
              <span>Server /data</span>
            </button>
            <button
              onClick={() => {
                setIngestionMode('s3_stream');
                if (s3AccessKey && s3SecretKey && s3Bucket && !s3Connected) {
                  handleTestS3Connection();
                }
              }}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                ingestionMode === 's3_stream' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Cloud className="w-4 h-4 text-sky-300" />
              <span>AWS S3 Stream</span>
            </button>
            <button
              onClick={() => setIngestionMode('upload')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                ingestionMode === 'upload' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload File</span>
            </button>
          </div>

          {/* MODE A: PRE-STAGED SERVER /DATA DATASETS */}
          {ingestionMode === 'server' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-950/80 border border-sky-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-sky-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-white">
                      Select Pre-Staged Dataset in /data
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={fetchServerDatasets}
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 transition"
                    title="Refresh /data datasets"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </div>

                {serverDatasets.length === 0 ? (
                  <div className="p-4 rounded-lg bg-slate-900 border border-white/5 text-center text-xs text-slate-400">
                    No datasets or files found in <code className="text-sky-300">/data</code>. Mount your host folder to <code className="text-sky-300">./data:/data</code> in docker-compose.yml.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="text-[11px] font-bold uppercase text-slate-400">Available Server Datasets ({serverDatasets.length})</label>
                    <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto custom-scrollbar">
                      {serverDatasets.map(ds => {
                        const isSelected = selectedDataset === ds.name;
                        return (
                          <div
                            key={ds.name}
                            onClick={() => handleDatasetChange(ds.name)}
                            className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                              isSelected
                                ? 'bg-sky-950/50 border-sky-500 ring-1 ring-sky-500/50 shadow-md'
                                : 'bg-slate-900/60 border-white/5 hover:border-white/20 hover:bg-slate-900'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`p-2 rounded-lg ${isSelected ? 'bg-sky-500/20 text-sky-400' : 'bg-slate-800 text-slate-400'}`}>
                                {ds.is_directory ? <Folder className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                              </div>
                              <div>
                                <div className="text-xs font-bold text-white font-mono">{ds.name}</div>
                                <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                                  <span>{ds.file_count} file{ds.file_count > 1 ? 's' : ''}</span>
                                  <span>•</span>
                                  <span className="text-sky-300 font-bold">{ds.size_mb} MB</span>
                                  {ds.is_parquet && (
                                    <span className="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 text-[10px] font-mono border border-amber-500/20">
                                      Parquet
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* MODE B: DIRECT FILE UPLOAD */}
          {ingestionMode === 'upload' && (
            <div className="space-y-4">
              <div className="p-6 rounded-xl bg-slate-950/80 border border-dashed border-sky-500/40 text-center space-y-3">
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  onChange={handleFileChange}
                  accept=".csv,.parquet,.pq,.json,.tsv"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer flex flex-col items-center justify-center gap-2 group"
                >
                  <div className="p-3 rounded-full bg-sky-500/10 text-sky-400 group-hover:bg-sky-500/20 transition">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <div className="text-xs font-bold text-white">
                    {file ? file.name : "Click to select a data file (.parquet, .csv, .json)"}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB selected` : "Drag and drop or browse from local filesystem"}
                  </div>
                </label>
              </div>

              {previewLoading && (
                <div className="p-4 rounded-xl bg-slate-900 border border-white/5 flex items-center justify-center gap-2 text-xs text-sky-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Inspecting file schema & inferring data types...</span>
                </div>
              )}

              {schemaPreview && (
                <div className="p-4 rounded-xl bg-slate-950/80 border border-sky-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-sky-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" /> Schema & Data Preview ({schemaPreview.columns?.length || 0} columns)
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 uppercase">
                      {schemaPreview.file_format || 'auto-detected'}
                    </span>
                  </div>

                  <div className="overflow-x-auto max-h-48 border border-white/5 rounded-lg custom-scrollbar">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-slate-900 text-slate-300 font-mono sticky top-0">
                        <tr>
                          {schemaPreview.columns?.map(col => (
                            <th key={col} className="px-3 py-1.5 border-b border-white/10 font-semibold">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 font-mono text-slate-300">
                        {schemaPreview.preview_data?.map((row, idx) => (
                          <tr key={idx} className="hover:bg-white/5">
                            {schemaPreview.columns?.map(col => (
                              <td key={col} className="px-3 py-1 truncate max-w-[150px]">{String(row[col] ?? '')}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* MODE C: AWS S3 CLOUD STREAM & FILE EXPLORER */}
          {ingestionMode === 's3_stream' && (
            <div className="space-y-4">
              
              {/* S3 Credentials & Bucket Configuration Card */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-indigo-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cloud className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-white">
                      AWS S3 Connection & Bucket Settings
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {s3Connected ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Connected
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        Not Connected
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => setIsS3ConfigExpanded(!isS3ConfigExpanded)}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400"
                    >
                      {isS3ConfigExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {isS3ConfigExpanded && (
                  <div className="space-y-3 pt-2 border-t border-white/5 animate-in fade-in duration-150">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-300 mb-1">
                          AWS Access Key ID
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            placeholder="e.g. AWS_ACCESS_KEY_ID"
                            value={s3AccessKey}
                            onChange={(e) => setS3AccessKey(e.target.value)}
                            className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-[11px] font-bold text-slate-300 mb-1">
                          AWS Secret Access Key
                        </label>
                        <div className="relative">
                          <input
                            type={showSecretKey ? "text" : "password"}
                            placeholder="e.g. AWS_SECRET_ACCESS_KEY"
                            value={s3SecretKey}
                            onChange={(e) => setS3SecretKey(e.target.value)}
                            className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500 pr-9"
                          />
                          <button
                            type="button"
                            onClick={() => setShowSecretKey(!showSecretKey)}
                            className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-200"
                          >
                            {showSecretKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-300 mb-1">
                          AWS Region
                        </label>
                        <select
                          value={s3Region}
                          onChange={(e) => setS3Region(e.target.value)}
                          className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                        >
                          <option value="us-east-1">US East (N. Virginia) [us-east-1]</option>
                          <option value="us-east-2">US East (Ohio) [us-east-2]</option>
                          <option value="us-west-1">US West (N. California) [us-west-1]</option>
                          <option value="us-west-2">US West (Oregon) [us-west-2]</option>
                          <option value="ap-south-1">Asia Pacific (Mumbai) [ap-south-1]</option>
                          <option value="ap-southeast-1">Asia Pacific (Singapore) [ap-southeast-1]</option>
                          <option value="ap-northeast-1">Asia Pacific (Tokyo) [ap-northeast-1]</option>
                          <option value="eu-west-1">Europe (Ireland) [eu-west-1]</option>
                          <option value="eu-central-1">Europe (Frankfurt) [eu-central-1]</option>
                          <option value="ca-central-1">Canada (Central) [ca-central-1]</option>
                          <option value="sa-east-1">South America (São Paulo) [sa-east-1]</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-bold text-slate-300 mb-1">
                          S3 Bucket Name
                        </label>
                        {s3BucketsList.length > 0 ? (
                          <div className="flex gap-2">
                            <select
                              value={s3Bucket}
                              onChange={(e) => {
                                setS3Bucket(e.target.value);
                                browseS3Folder(e.target.value, '');
                              }}
                              className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500 font-bold text-sky-300"
                            >
                              {s3BucketsList.map(b => (
                                <option key={b} value={b}>{b}</option>
                              ))}
                            </select>
                          </div>
                        ) : (
                          <input
                            type="text"
                            placeholder="e.g. enterprise-raw-data-lake"
                            value={s3Bucket}
                            onChange={(e) => setS3Bucket(e.target.value)}
                            className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500 font-bold text-sky-300"
                          />
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <button
                        type="button"
                        onClick={handleTestS3Connection}
                        disabled={s3Connecting}
                        className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition flex items-center gap-2 disabled:opacity-50"
                      >
                        {s3Connecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Globe className="w-3.5 h-3.5" />}
                        Connect & Explore S3
                      </button>

                      {s3Bucket && (
                        <button
                          type="button"
                          onClick={() => browseS3Folder(s3Bucket, s3Prefix)}
                          disabled={s3Browsing}
                          className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold border border-white/10 flex items-center gap-1.5 transition"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${s3Browsing ? 'animate-spin' : ''}`} />
                          Refresh Folder
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* S3 BREADCRUMB & DIRECTORY EXPLORER */}
              <div className="space-y-3 p-4 rounded-xl bg-slate-950/80 border border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <FolderOpen className="w-4 h-4 text-sky-400" />
                    S3 Bucket Explorer
                  </span>

                  {s3Files.length > 0 && (
                    <button
                      type="button"
                      onClick={toggleSelectAllS3Files}
                      className="text-[11px] text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1"
                    >
                      {s3SelectedFiles.length === filteredS3Files.length && filteredS3Files.length > 0 ? (
                        <>
                          <CheckSquare className="w-3.5 h-3.5 text-sky-400" />
                          Deselect All
                        </>
                      ) : (
                        <>
                          <Square className="w-3.5 h-3.5 text-slate-400" />
                          Select All ({filteredS3Files.length})
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* S3 Breadcrumb Path Navigation */}
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-900 border border-white/10 text-xs font-mono overflow-x-auto custom-scrollbar">
                  <span className="text-indigo-400 font-bold flex items-center gap-1">
                    <Cloud className="w-3.5 h-3.5" />
                    s3://
                  </span>
                  <button
                    type="button"
                    onClick={() => browseS3Folder(s3Bucket, '')}
                    className="text-sky-300 hover:underline font-bold"
                  >
                    {s3Bucket || 'bucket'}
                  </button>
                  <span className="text-slate-500">/</span>

                  {s3Prefix.split('/').filter(Boolean).map((part, idx, arr) => {
                    const subPath = arr.slice(0, idx + 1).join('/') + '/';
                    return (
                      <React.Fragment key={subPath}>
                        <button
                          type="button"
                          onClick={() => browseS3Folder(s3Bucket, subPath)}
                          className="text-slate-300 hover:text-sky-300 hover:underline"
                        >
                          {part}
                        </button>
                        <span className="text-slate-500">/</span>
                      </React.Fragment>
                    );
                  })}
                </div>

                {/* Search & Navigation Bar */}
                <div className="flex items-center gap-2">
                  {s3Prefix && (
                    <button
                      type="button"
                      onClick={() => browseS3Folder(s3Bucket, s3ParentPrefix)}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-white/10 flex items-center gap-1"
                      title="Navigate to parent directory"
                    >
                      <ArrowUp className="w-3.5 h-3.5 text-sky-400" />
                      Up
                    </button>
                  )}

                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search files in current S3 folder..."
                      value={s3SearchTerm}
                      onChange={(e) => setS3SearchTerm(e.target.value)}
                      className="w-full bg-slate-900 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>

                {/* S3 Folders & Files Listing */}
                {s3Browsing ? (
                  <div className="p-8 text-center text-xs text-sky-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Browsing S3 bucket contents...
                  </div>
                ) : s3Folders.length === 0 && s3Files.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-xl border border-white/5">
                    {!s3Connected 
                      ? "Enter AWS credentials above and click 'Connect & Explore S3' to browse buckets and folders."
                      : "This S3 folder is empty or contains no recognized objects."}
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-64 overflow-y-auto custom-scrollbar pr-1">
                    
                    {/* Subfolders */}
                    {s3Folders.map(f => (
                      <div
                        key={f.prefix}
                        onClick={() => browseS3Folder(s3Bucket, f.prefix)}
                        className="p-2.5 rounded-lg bg-slate-900/60 hover:bg-slate-800/80 border border-white/5 hover:border-sky-500/40 transition cursor-pointer flex items-center justify-between group"
                      >
                        <div className="flex items-center gap-2 font-mono text-xs text-slate-200">
                          <Folder className="w-4 h-4 text-sky-400 group-hover:text-sky-300" />
                          <span className="font-bold">{f.name}/</span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">Folder</span>
                      </div>
                    ))}

                    {/* Files */}
                    {filteredS3Files.map(f => {
                      const isSelected = s3SelectedFiles.includes(f.key);
                      return (
                        <div
                          key={f.key}
                          className={`p-2.5 rounded-lg border transition flex items-center justify-between ${
                            isSelected 
                              ? 'bg-sky-950/40 border-sky-500/60 shadow' 
                              : 'bg-slate-900/40 border-white/5 hover:border-white/20'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 flex-1">
                            <button
                              type="button"
                              onClick={() => toggleSelectS3File(f.key)}
                              className="text-slate-400 hover:text-sky-400"
                            >
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-sky-400" />
                              ) : (
                                <Square className="w-4 h-4" />
                              )}
                            </button>

                            <div className="min-w-0 flex-1 space-y-0.5">
                              <div className="font-mono text-xs text-white truncate font-semibold" title={f.key}>
                                {f.name}
                              </div>
                              <div className="text-[10px] text-slate-400 font-mono flex items-center gap-3">
                                <span className="text-emerald-400 font-bold">{f.size_formatted}</span>
                                <span>•</span>
                                <span>{f.last_modified}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 pl-2">
                            <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 text-slate-300 border border-white/10">
                              {f.format}
                            </span>

                            <button
                              type="button"
                              onClick={() => handlePreviewS3File(f.key)}
                              className="p-1 rounded bg-slate-800 hover:bg-sky-600/30 text-sky-300 border border-white/10"
                              title="Preview Schema and Data Sample"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* S3 Selection Summary */}
                <div className="flex items-center justify-between text-[11px] pt-2 border-t border-white/5 font-mono text-slate-400">
                  <span>
                    {s3SelectedFiles.length === 0 ? (
                      <span className="text-amber-400">
                        ⚡ Whole folder mode: Spark will read all files under <code>s3://{s3Bucket}/{s3Prefix}</code>
                      </span>
                    ) : (
                      <span className="text-sky-300 font-bold">
                        ✓ {s3SelectedFiles.length} specific file(s) selected
                      </span>
                    )}
                  </span>
                </div>
              </div>

              {/* S3 Preview Modal / Drawer */}
              {s3PreviewLoading && (
                <div className="p-4 rounded-xl bg-slate-950/80 border border-white/10 text-xs text-sky-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Inspecting S3 object schema...
                </div>
              )}

              {s3PreviewData && (
                <div className="p-4 rounded-xl bg-slate-950/90 border border-sky-500/40 space-y-3 animate-in fade-in duration-150">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold text-xs text-white">
                      <TableIcon className="w-4 h-4 text-sky-400" />
                      S3 Schema Preview: <span className="text-sky-300 font-mono">{s3PreviewData.key.split('/').pop()}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setS3PreviewData(null)}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto custom-scrollbar">
                    {s3PreviewData.columns.map(col => (
                      <span
                        key={col}
                        className="px-2 py-0.5 rounded bg-slate-900 border border-white/15 text-[10px] font-mono text-slate-300"
                      >
                        {col}
                      </span>
                    ))}
                  </div>

                  {s3PreviewData.preview_rows && s3PreviewData.preview_rows.length > 0 && (
                    <div className="overflow-x-auto max-h-36 custom-scrollbar rounded-lg border border-white/10">
                      <table className="w-full text-left text-[10px] font-mono">
                        <thead className="bg-slate-900 text-slate-400 sticky top-0">
                          <tr>
                            {s3PreviewData.columns.slice(0, 6).map(c => (
                              <th key={c} className="p-1.5 border-b border-white/10">{c}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {s3PreviewData.preview_rows.slice(0, 5).map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-white/5">
                              {s3PreviewData.columns.slice(0, 6).map(c => (
                                <td key={c} className="p-1.5 text-slate-300 truncate max-w-xs">{row[c]}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Streaming Pipeline Mode Switcher */}
              <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-slate-900/80 border border-white/10">
                <button
                  type="button"
                  onClick={() => setS3StreamMode('batch')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                    s3StreamMode === 'batch'
                      ? 'bg-sky-600 text-white shadow'
                      : 'bg-slate-950/40 text-slate-400 hover:text-white'
                  }`}
                >
                  <Play className="w-3.5 h-3.5" />
                  Batch Ingestion
                </button>
                <button
                  type="button"
                  onClick={() => setS3StreamMode('stream')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                    s3StreamMode === 'stream'
                      ? 'bg-indigo-600 text-white shadow'
                      : 'bg-slate-950/40 text-slate-400 hover:text-white'
                  }`}
                >
                  <Radio className="w-3.5 h-3.5 animate-pulse text-rose-400" />
                  Structured Streaming
                </button>
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

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase">Chunk Size:</label>
              <input
                type="number"
                min="1"
                max="500"
                value={chunkSize}
                onChange={(e) => setChunkSize(e.target.value)}
                placeholder="50"
                className="w-full bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
              />
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
            onClick={
              ingestionMode === 'server' 
                ? handleSubmitServerDataset 
                : ingestionMode === 's3_stream' 
                ? handleSubmitS3Stream 
                : handleSubmitUpload
            }
            disabled={submitting}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2 transition disabled:opacity-40"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            {ingestionMode === 's3_stream'
              ? (s3StreamMode === 'stream' ? '🌊 Launch AWS S3 Structured Stream' : '⚡ Execute AWS S3 Batch Ingestion')
              : '🚀 Execute Distributed Ingestion Pipeline'}
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
