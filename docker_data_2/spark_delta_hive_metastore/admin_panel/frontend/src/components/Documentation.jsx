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
  ExternalLink
} from 'lucide-react';

export default function Documentation() {
  const [activeDoc, setActiveDoc] = useState('arch'); // 'arch', 'delta', 'tuning', 'cli'

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
          { id: 'delta', label: '⏳ Delta Lake & ACID SQL Cheatsheet' },
          { id: 'tuning', label: '⚙️ Spark Dynamic Resource Allocation' },
          { id: 'cli', label: '💻 Spark Submit & CLI Runbook' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveDoc(t.id)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
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
