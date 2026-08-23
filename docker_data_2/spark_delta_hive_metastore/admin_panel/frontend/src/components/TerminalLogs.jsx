import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, Play, Square, Trash2, Download, RefreshCw } from 'lucide-react';

export default function TerminalLogs({ services }) {
  const [selectedContainer, setSelectedContainer] = useState('spark');
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalEndRef = useRef(null);
  const wsRef = useRef(null);

  const runningContainers = services.filter(s => s.status === 'RUNNING').map(s => s.container || s.compose_service);

  useEffect(() => {
    if (!selectedContainer) return;
    setLogs([`[Connecting to WebSocket log stream for '${selectedContainer}'...]`]);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs/${selectedContainer}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLogs(prev => [...prev, `[Connected: Streaming stdout/stderr in real-time...]`]);
    };

    ws.onmessage = (event) => {
      setLogs(prev => {
        const updated = [...prev, event.data];
        return updated.slice(-1000); // Keep last 1000 lines
      });
    };

    ws.onerror = (err) => {
      setLogs(prev => [...prev, `[WebSocket Error: Stream disconnected]`]);
    };

    return () => {
      if (ws) ws.close();
    };
  }, [selectedContainer]);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="glass-card p-6 border-l-4 border-l-emerald-500 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
            <TerminalIcon className="w-5 h-5 text-emerald-400" />
            Live Container Log Streamer (WebSocket Push)
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Zero-polling live stdout/stderr event stream connected directly to Docker engine daemon over WebSocket.
          </p>
        </div>

        {/* Container Selector & Actions */}
        <div className="flex items-center gap-3">
          <select
            value={selectedContainer}
            onChange={(e) => setSelectedContainer(e.target.value)}
            className="bg-slate-900 border border-white/15 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
          >
            {services.map(s => (
              <option key={s.key} value={s.container || s.compose_service}>
                {s.icon} {s.name} ({s.status})
              </option>
            ))}
          </select>

          <button
            onClick={() => setLogs([])}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-400 hover:text-white transition"
            title="Clear Console"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* TERMINAL DISPLAY */}
      <div className="glass-card p-4 space-y-2 border border-white/10">
        <div className="flex items-center justify-between px-2 pb-2 border-b border-white/10 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono font-bold text-slate-200">Container: {selectedContainer}</span>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
            <span>Auto-Scroll</span>
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
