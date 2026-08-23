import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import PodOrchestrator from './components/PodOrchestrator';
import SqlStudio from './components/SqlStudio';
import SparkTuning from './components/SparkTuning';
import MetastoreCatalog from './components/MetastoreCatalog';
import TerminalLogs from './components/TerminalLogs';
import Diagnostics from './components/Diagnostics';
import ClusterHealth from './components/ClusterHealth';
import DeltaMaintenance from './components/DeltaMaintenance';

export default function App() {
  const [activeTab, setActiveTabState] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('tab') || 'orchestrator';
  });

  const [services, setServices] = useState([]);
  const [presets, setPresets] = useState({});
  const [wsConnected, setWsConnected] = useState(false);
  const [activeProfile, setActiveProfile] = useState('Heavy Analytical');
  const wsRef = useRef(null);

  const setActiveTab = (tabId) => {
    setActiveTabState(tabId);
    const url = new URL(window.location);
    url.searchParams.set('tab', tabId);
    window.history.pushState({}, '', url);
  };

  const fetchMatrix = async () => {
    try {
      const res = await fetch('/api/orchestrator/matrix');
      const data = await res.json();
      setServices(data.services || []);
      setPresets(data.presets || {});
    } catch (err) {
      console.error("Failed to fetch service matrix", err);
    }
  };

  useEffect(() => {
    fetchMatrix();

    // Setup Real-Time WebSocket Connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/events`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Instant event-driven state update without polling
        if (msg.type === 'DOCKER_CONTAINER_EVENT' || msg.type === 'ORCHESTRATOR_ACTION') {
          fetchMatrix();
        }
      } catch (err) {
        console.error(err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const unhealthyCount = services.filter(s => s.status === 'UNHEALTHY').length;
  const clusterOnline = unhealthyCount === 0;

  return (
    <div className="min-h-screen bg-[#07090e] text-[#f8fafc] flex flex-col selection:bg-indigo-500/30">
      
      {/* Executive Top Bar */}
      <Header
        clusterOnline={clusterOnline}
        unhealthyCount={unhealthyCount}
        wsConnected={wsConnected}
        activeProfile={activeProfile}
      />

      {/* Main App Workspace */}
      <div className="flex-1 flex max-w-[1700px] w-full mx-auto">
        
        {/* Navigation Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Dynamic Content Viewport */}
        <main className="flex-1 p-8 overflow-y-auto custom-scrollbar">
          {activeTab === 'orchestrator' && (
            <PodOrchestrator services={services} presets={presets} onRefresh={fetchMatrix} />
          )}

          {activeTab === 'sql_studio' && (
            <SqlStudio />
          )}

          {activeTab === 'tuning' && (
            <SparkTuning onProfileChange={setActiveProfile} />
          )}

          {activeTab === 'metastore' && (
            <MetastoreCatalog />
          )}

          {activeTab === 'logs' && (
            <TerminalLogs services={services} />
          )}

          {activeTab === 'diagnostics' && (
            <Diagnostics />
          )}

          {activeTab === 'health' && (
            <ClusterHealth services={services} onRefresh={fetchMatrix} />
          )}

          {activeTab === 'delta_time' && (
            <DeltaMaintenance />
          )}

          {['ingestion', 'backup', 'purge', 'docs'].includes(activeTab) && (
            <div className="glass-card p-12 text-center space-y-3">
              <div className="text-3xl">🚀</div>
              <h3 className="text-lg font-bold text-white capitalize">{activeTab.replace('_', ' ')} Studio</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Ready for next-generation decoupled pipeline execution. All backend FastAPI endpoints are live on port 8501.
              </p>
            </div>
          )}
        </main>

      </div>

    </div>
  );
}
