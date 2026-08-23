import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal as TerminalIcon, 
  Play, 
  Square, 
  Trash2, 
  Download, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle,
  Copy,
  ChevronDown
} from 'lucide-react';

export default function TerminalLogs({ services = [] }) {
  const [selectedContainer, setSelectedContainer] = useState('spark');
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [streamStatus, setStreamStatus] = useState('connecting'); // 'connecting', 'connected', 'disconnected'
  const [reconnectKey, setReconnectKey] = useState(0);
  const terminalEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!selectedContainer) return;
    setLogs([`[Connecting to WebSocket log stream for '${selectedContainer}'...]`]);
    setStreamStatus('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs/${selectedContainer}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStreamStatus('connected');
      setLogs(prev => [...prev, `[Connected: Streaming stdout/stderr in real-time...]`]);
    };

    ws.onmessage = (event) => {
      setLogs(prev => {
        const updated = [...prev, event.data];
        return updated.slice(-1500); // Keep last 1500 lines
      });
    };

    ws.onclose = () => {
      setStreamStatus('disconnected');
    };

    ws.onerror = (err) => {
      setStreamStatus('disconnected');
      setLogs(prev => [...prev, `[WebSocket Notice: Stream disconnected / Container not active]`]);
    };

    return () => {
      if (ws) ws.close();
    };
  }, [selectedContainer, reconnectKey]);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleDownload = () => {
    const blob = new Blob([logs.join('')], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${selectedContainer}_logs.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join(''));
  };

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-emerald-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <TerminalIcon className="w-5 h-5 text-emerald-400" />
            Live Container Log Streamer (WebSocket Push)
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl">
            Real-time asynchronous stdout/stderr stream directly connected to the Docker engine daemon over WebSockets with zero HTTP polling.
          </p>
        </div>

        {/* Container Selector & Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-2">
            <select
              value={selectedContainer}
              onChange={(e) => setSelectedContainer(e.target.value)}
              className="bg-slate-900 border border-white/15 rounded-xl px-3.5 py-2 text-xs font-mono font-bold text-white focus:outline-none focus:border-emerald-500"
            >
              {services.map(s => (
                <option key={s.key} value={s.container || s.compose_service}>
                  {s.icon} {s.name} ({s.status})
                </option>
              ))}
            </select>

            <button
              onClick={() => setReconnectKey(k => k + 1)}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-300 hover:text-white transition"
              title="Reconnect Stream"
            >
              <RefreshCw className={`w-4 h-4 ${streamStatus === 'connecting' ? 'animate-spin text-sky-400' : ''}`} />
            </button>
          </div>

          <div className="flex items-center gap-1.5 pl-2 border-l border-white/10">
            <button
              onClick={handleCopy}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-400 hover:text-white transition"
              title="Copy All Logs"
            >
              <Copy className="w-4 h-4" />
            </button>

            <button
              onClick={handleDownload}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-400 hover:text-white transition"
              title="Download Logs as .txt"
            >
              <Download className="w-4 h-4" />
            </button>

            <button
              onClick={() => setLogs([])}
              className="p-2 rounded-xl bg-slate-800 hover:bg-rose-950/40 border border-white/10 text-slate-400 hover:text-rose-400 transition"
              title="Clear Console"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* TERMINAL DISPLAY */}
      <div className="glass-card p-4 space-y-2 border border-white/10">
        <div className="flex items-center justify-between px-2 pb-2 border-b border-white/10 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="flex h-2 w-2 relative">
                {streamStatus === 'connected' && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  streamStatus === 'connected' ? 'bg-emerald-500' : streamStatus === 'connecting' ? 'bg-amber-400' : 'bg-rose-500'
                }`}></span>
              </span>
              <span className="font-mono font-bold text-slate-200">Container: {selectedContainer}</span>
            </div>

            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
              streamStatus === 'connected' 
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                : streamStatus === 'connecting'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
            }`}>
              {streamStatus === 'connected' ? '● LIVE STREAMING' : streamStatus === 'connecting' ? 'CONNECTING...' : 'DISCONNECTED'}
            </span>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
            <span className="text-[11px] text-slate-400">Auto-Scroll</span>
          </label>
        </div>

        <div className="bg-[#030712] rounded-xl p-4 font-mono text-[11px] leading-relaxed text-emerald-400/90 h-[560px] overflow-y-auto custom-scrollbar whitespace-pre-wrap selection:bg-emerald-500/20">
          {logs.map((line, idx) => (
            <div key={idx} className="hover:bg-white/[0.02] py-0.5">{line}</div>
          ))}
          <div ref={terminalEndRef} />
        </div>
      </div>

    </div>
  );
}
