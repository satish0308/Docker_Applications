import React, { useState } from 'react';
import { 
  BookOpen, 
  Layers, 
  Cpu, 
  Database, 
  Terminal, 
  ShieldCheck, 
  Zap, 
  Code,
  CheckCircle2,
  ExternalLink,
  Cloud,
  Copy,
  Check
} from 'lucide-react';

export default function Documentation() {
  const [activeDoc, setActiveDoc] = useState('arch'); // 'arch', 's3_cmds', 'delta', 'tuning', 'cli'
  const [copiedId, setCopiedId] = useState(null);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="glass-card p-6 border-l-4 border-l-indigo-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            📚 Platform Documentation, Architectural Blueprints & Runbooks
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            Complete reference manuals for Apache Spark 3.5, Delta Lake 3.2, Hive Metastore 3.1.3, Livy REST, and Dynamic Resource Allocation.
          </p>
        </div>
      </div>

      {/* Doc Navigation Tabs */}
      <div className="flex items-center gap-2 p-1.5 rounded-xl bg-slate-900 border border-white/10 overflow-x-auto">
        {[
          { id: 'arch', label: '🏗️ Platform Architecture & Port Map' },
          { id: 's3_cmds', label: '☁️ S3A DataFrame Storage Commands' },
          { id: 'delta', label: '⏳ Delta Lake & ACID SQL Cheatsheet' },
          { id: 'tuning', label: '⚙️ Spark Dynamic Resource Allocation' },
          { id: 'cli', label: '💻 Spark Submit & CLI Runbook' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveDoc(t.id)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition whitespace-nowrap ${
              activeDoc === t.id ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* DOC CONTENT 1: ARCHITECTURE */}
      {activeDoc === 'arch' && (
        <div className="glass-card p-6 space-y-6">
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Distributed Platform Blueprint & Network Port Map
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="font-bold text-sky-400 text-sm">⚡ Compute Tier</div>
              <div>Spark Master: <span className="text-white font-bold">Port 7077 / 8089</span></div>
              <div>Spark History: <span className="text-white font-bold">Port 18080</span></div>
              <div>Spark Workers: <span className="text-white font-bold">Port 8091–8094</span></div>
              <div>Spark Thrift JDBC: <span className="text-white font-bold">Port 10000</span></div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="font-bold text-emerald-400 text-sm">📦 Storage & Metastore Tier</div>
              <div>PostgreSQL Metastore: <span className="text-white font-bold">Port 5432</span></div>
              <div>Hive Metastore Thrift: <span className="text-white font-bold">Port 9083</span></div>
              <div>HDFS NameNode: <span className="text-white font-bold">Port 9870 / 9000</span></div>
              <div>MinIO S3 API: <span className="text-white font-bold">Port 9000 / 9001</span></div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="font-bold text-amber-400 text-sm">🎨 Interactive Studios</div>
              <div>Hue Analytics Studio: <span className="text-white font-bold">Port 8888</span></div>
              <div>Livy REST Engine: <span className="text-white font-bold">Port 8998</span></div>
              <div>JupyterLab Data Science: <span className="text-white font-bold">Port 8889</span></div>
              <div>pgAdmin 4 Console: <span className="text-white font-bold">Port 8081</span></div>
            </div>
          </div>
        </div>
      )}

      {/* DOC CONTENT: S3A DATAFRAME STORAGE CHEATSHEET */}
      {activeDoc === 's3_cmds' && (
        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <Cloud className="w-5 h-5 text-indigo-400" />
                PySpark S3A DataFrame Storage & Metastore Commands
              </h3>
              <p className="text-xs text-slate-300 mt-1">
                Standard syntax for saving PySpark DataFrames (<code className="text-sky-300 font-mono">df</code>) to <code className="text-sky-300 font-mono">s3a://</code> locations on MinIO Lakehouse and AWS S3.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 text-xs font-mono">
            
            {/* CARD 1: DELTA LAKE (ACID) */}
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sky-400 font-bold text-sm flex items-center gap-1.5">
                    ⚡ 1. Save as Delta Lake (ACID Lakehouse)
                  </span>
                  <button
                    onClick={() => handleCopy('delta_save', `df.write \\
  .format("delta") \\
  .mode("overwrite") \\
  .option("path", "s3a://warehouse/my_delta_table") \\
  .saveAsTable("default.my_delta_table")`)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 transition"
                  >
                    {copiedId === 'delta_save' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedId === 'delta_save' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 font-sans">
                  Saves directly to MinIO/S3A with full ACID transaction log and registers in Hive Metastore.
                </p>
                <pre className="p-3 rounded-lg bg-slate-900 border border-white/5 text-slate-200 overflow-x-auto custom-scrollbar">
{`# A. Save as Raw Delta Files:
df.write \\
  .format("delta") \\
  .mode("overwrite") \\
  .save("s3a://warehouse/my_delta_table")

# B. Save & Register in Metastore Table:
df.write \\
  .format("delta") \\
  .mode("append") \\
  .option("path", "s3a://warehouse/my_delta_table") \\
  .saveAsTable("default.my_delta_table")`}
                </pre>
              </div>
            </div>

            {/* CARD 2: APACHE PARQUET */}
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-emerald-400 font-bold text-sm flex items-center gap-1.5">
                    📦 2. Save as Apache Parquet
                  </span>
                  <button
                    onClick={() => handleCopy('parquet_save', `df.write \\
  .format("parquet") \\
  .mode("overwrite") \\
  .option("path", "s3a://warehouse/my_parquet_table") \\
  .saveAsTable("default.my_parquet_table")`)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 transition"
                  >
                    {copiedId === 'parquet_save' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedId === 'parquet_save' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 font-sans">
                  Standard columnar Parquet export with Snappy compression.
                </p>
                <pre className="p-3 rounded-lg bg-slate-900 border border-white/5 text-slate-200 overflow-x-auto custom-scrollbar">
{`# A. Raw Parquet Files:
df.write \\
  .format("parquet") \\
  .mode("overwrite") \\
  .save("s3a://warehouse/my_parquet_data")

# B. Direct Shortcut:
df.write.parquet("s3a://warehouse/my_parquet_data", mode="overwrite")

# C. Register in Metastore:
df.write \\
  .format("parquet") \\
  .mode("append") \\
  .option("path", "s3a://warehouse/my_parquet_table") \\
  .saveAsTable("default.my_parquet_table")`}
                </pre>
              </div>
            </div>

            {/* CARD 3: PARTITIONING & MULTI-COLUMN INDEXING */}
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-amber-400 font-bold text-sm flex items-center gap-1.5">
                    🗂️ 3. Save with Partitioning
                  </span>
                  <button
                    onClick={() => handleCopy('partition_save', `df.write \\
  .format("delta") \\
  .partitionBy("country", "year") \\
  .mode("append") \\
  .save("s3a://warehouse/sales_partitioned")`)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 transition"
                  >
                    {copiedId === 'partition_save' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedId === 'partition_save' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 font-sans">
                  Hierarchical folder partitioning on storage for fast partition-pruned SQL queries.
                </p>
                <pre className="p-3 rounded-lg bg-slate-900 border border-white/5 text-slate-200 overflow-x-auto custom-scrollbar">
{`# Multi-column Partitioning:
df.write \\
  .format("delta") \\
  .partitionBy("country", "year") \\
  .mode("append") \\
  .save("s3a://warehouse/sales_partitioned")`}
                </pre>
              </div>
            </div>

            {/* CARD 4: CSV & JSON EXPORTS */}
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-purple-400 font-bold text-sm flex items-center gap-1.5">
                    📄 4. Save as CSV / JSON
                  </span>
                  <button
                    onClick={() => handleCopy('csv_save', `df.write \\
  .format("csv") \\
  .option("header", "true") \\
  .mode("overwrite") \\
  .save("s3a://warehouse/my_csv_exports")`)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 transition"
                  >
                    {copiedId === 'csv_save' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedId === 'csv_save' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 font-sans">
                  Export to CSV with header row or multi-line / line-delimited JSON.
                </p>
                <pre className="p-3 rounded-lg bg-slate-900 border border-white/5 text-slate-200 overflow-x-auto custom-scrollbar">
{`# A. CSV with Headers:
df.write \\
  .format("csv") \\
  .option("header", "true") \\
  .mode("overwrite") \\
  .save("s3a://warehouse/my_csv_exports")

# B. JSON:
df.write \\
  .format("json") \\
  .mode("overwrite") \\
  .save("s3a://warehouse/my_json_data")`}
                </pre>
              </div>
            </div>

          </div>

          {/* S3A RUNTIME HADOOP CONFIGURATION */}
          <div className="p-5 rounded-xl bg-slate-950 border border-indigo-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-white font-bold text-sm flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
                5. S3A Hadoop Credential Setup in PySpark (Local MinIO vs External AWS S3)
              </span>
              <button
                onClick={() => handleCopy('hadoop_conf', `hconf = spark.sparkContext._jsc.hadoopConfiguration()
# Local MinIO Lakehouse (s3a://warehouse/):
hconf.set("fs.s3a.endpoint", "http://minio:9000")
hconf.set("fs.s3a.access.key", "minioadmin")
hconf.set("fs.s3a.secret.key", "minioadmin123")
hconf.set("fs.s3a.path.style.access", "true")
hconf.set("fs.s3a.connection.ssl.enabled", "false")

# External AWS S3 Per-Bucket Isolation (s3a://my-aws-bucket/):
bucket = "my-aws-bucket"
region = "eu-central-1"
hconf.set(f"fs.s3a.bucket.{bucket}.endpoint", f"s3.{region}.amazonaws.com")
hconf.set(f"fs.s3a.bucket.{bucket}.access.key", "YOUR_AWS_ACCESS_KEY")
hconf.set(f"fs.s3a.bucket.{bucket}.secret.key", "YOUR_AWS_SECRET_KEY")
hconf.set(f"fs.s3a.bucket.{bucket}.path.style.access", "false")
hconf.set(f"fs.s3a.bucket.{bucket}.connection.ssl.enabled", "true")`)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 transition"
              >
                {copiedId === 'hadoop_conf' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedId === 'hadoop_conf' ? 'Copied' : 'Copy'}
              </button>
            </div>

            <pre className="p-3 rounded-lg bg-slate-900 border border-white/5 text-slate-200 text-xs font-mono overflow-x-auto custom-scrollbar">
{`hconf = spark.sparkContext._jsc.hadoopConfiguration()

# 🪣 Local MinIO Lakehouse (s3a://warehouse/):
hconf.set("fs.s3a.endpoint", "http://minio:9000")
hconf.set("fs.s3a.access.key", "minioadmin")
hconf.set("fs.s3a.secret.key", "minioadmin123")
hconf.set("fs.s3a.path.style.access", "true")
hconf.set("fs.s3a.connection.ssl.enabled", "false")

# ☁️ External AWS S3 Bucket Isolation (s3a://my-aws-bucket/):
bucket = "my-aws-bucket"
region = "eu-central-1"  # or us-east-1, us-west-2, ap-south-1, etc.
hconf.set(f"fs.s3a.bucket.{bucket}.endpoint", f"s3.{region}.amazonaws.com")
hconf.set(f"fs.s3a.bucket.{bucket}.access.key", "YOUR_AWS_ACCESS_KEY")
hconf.set(f"fs.s3a.bucket.{bucket}.secret.key", "YOUR_AWS_SECRET_KEY")
hconf.set(f"fs.s3a.bucket.{bucket}.path.style.access", "false")
hconf.set(f"fs.s3a.bucket.{bucket}.connection.ssl.enabled", "true")

# Save directly to AWS S3:
df.write.format("delta").mode("overwrite").save(f"s3a://{bucket}/raw_data/")`}
            </pre>
          </div>
        </div>
      )}

      {/* DOC CONTENT 2: DELTA LAKE */}
      {activeDoc === 'delta' && (
        <div className="glass-card p-6 space-y-5">
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-sky-400" />
            Delta Lake SQL Quick Reference
          </h3>

          <div className="space-y-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="text-indigo-400 font-bold">1. Time-Travel Querying (Point-in-Time)</div>
              <pre className="text-slate-300">-- Query by version ID{"\n"}SELECT * FROM sales VERSION AS OF 2;{"\n\n"}-- Query by timestamp{"\n"}SELECT * FROM sales TIMESTAMP AS OF '2026-08-20 14:00:00';</pre>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="text-emerald-400 font-bold">2. Compaction & Multidimensional Z-Ordering</div>
              <pre className="text-slate-300">-- Coalesce small files and cluster index on customer_id{"\n"}OPTIMIZE sales ZORDER BY (customer_id, order_date);</pre>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="text-amber-400 font-bold">3. Dead Storage Reclamation (VACUUM)</div>
              <pre className="text-slate-300">-- Delete expired snapshot files older than 168 hours (7 days){"\n"}SET spark.databricks.delta.vacuum.parallelDelete.enabled = true;{"\n"}VACUUM sales RETAIN 168 HOURS;</pre>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
              <div className="text-rose-400 font-bold">4. Instant In-Place Table Rollback</div>
              <pre className="text-slate-300">-- Restore table in place to exact historical state{"\n"}RESTORE TABLE sales TO VERSION AS OF 1;</pre>
            </div>
          </div>
        </div>
      )}

      {/* DOC CONTENT 3: TUNING */}
      {activeDoc === 'tuning' && (
        <div className="glass-card p-6 space-y-5">
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-amber-400" />
            Dynamic Resource Allocation (DRA) & AQE Architecture
          </h3>

          <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-3 text-xs leading-relaxed text-slate-300">
            <p>
              The platform incorporates <b>Monolithic Single-Executor Dynamic Sizing</b>. Rather than splitting memory across tiny executors with GC overhead, each worker runs an optimized high-throughput executor container with Adaptive Query Execution (AQE).
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 font-mono text-[11px]">
              <div className="p-3 rounded-lg bg-slate-900 border border-white/5 space-y-1">
                <div className="font-bold text-sky-400">Adaptive Query Execution (AQE)</div>
                <div>spark.sql.adaptive.enabled = true</div>
                <div>spark.sql.adaptive.coalescePartitions.enabled = true</div>
                <div>spark.sql.adaptive.skewJoin.enabled = true</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-white/5 space-y-1">
                <div className="font-bold text-amber-400">Off-Heap Memory & GC Avoidance</div>
                <div>spark.memory.offHeap.enabled = true</div>
                <div>spark.memory.offHeap.size = 1g–2g</div>
                <div>spark.serializer = KryoSerializer</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DOC CONTENT 4: CLI */}
      {activeDoc === 'cli' && (
        <div className="glass-card p-6 space-y-5">
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            CLI & Production Spark Submit Commands
          </h3>

          <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2 font-mono text-xs text-slate-300">
            <div className="text-slate-400"># Direct Spark-Submit with S3 and Delta dependencies</div>
            <pre className="text-emerald-400 whitespace-pre-wrap">
docker exec -it spark /opt/spark/bin/spark-submit \
  --master spark://spark:7077 \
  --driver-memory 4g \
  --executor-memory 8g \
  --conf spark.sql.shuffle.partitions=200 \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minioadmin \
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin123 \
  /opt/spark/scripts/my_pipeline.py
            </pre>
          </div>
        </div>
      )}

    </div>
  );
}
