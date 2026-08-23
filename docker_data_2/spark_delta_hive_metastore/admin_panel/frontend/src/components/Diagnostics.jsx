import React, { useState } from 'react';
import { Stethoscope, Play, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function Diagnostics() {
  const [output, setOutput] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/diagnostics/run', { method: 'POST' });
      const data = await res.json();
      setOutput(data);
    } catch (err) {
      setOutput({ exit_code: 1, stdout: '', stderr: String(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      <div className="glass-card p-6 border-l-4 border-l-rose-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <Stethoscope className="w-5 h-5 text-rose-400" />
            Automated Multi-Port Diagnostic Prober
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Probes all distributed container sockets (PostgreSQL 5432, HDFS 9000/9870, Spark 7077/8089/18080, Livy 8998, Hive 10000, Hue 8888, Keycloak 8080, MinIO 9000/9001).
          </p>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:opacity-90 text-white font-bold text-xs shadow-lg shadow-rose-500/20 flex items-center gap-2 transition disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          {loading ? 'Probing Cluster Sockets...' : '⚡ Run Full Diagnostics Probe'}
        </button>
      </div>

      {output && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                output.exit_code === 0 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              }`}>
                {output.exit_code === 0 ? 'ALL SOCKETS HEALTHY' : 'DIAGNOSTIC ISSUES DETECTED'}
              </span>
            </div>
          </div>

          <div className="bg-[#030712] rounded-xl p-4 font-mono text-xs text-slate-300 leading-relaxed overflow-x-auto border border-white/10 whitespace-pre-wrap">
            {output.stdout || output.stderr}
          </div>
        </div>
      )}

    </div>
  );
}
