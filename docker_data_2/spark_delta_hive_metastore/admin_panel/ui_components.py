"""
Admin Panel v2 UI Component Library
Provides modern glassmorphism, responsive cards, neon status pills, executive headers, and custom design tokens.
"""

import streamlit as st

def inject_v2_theme():
    """Injects the modern, luxury SaaS enterprise dark theme CSS."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* Global Typography & Reset */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #07090e !important;
        color: #f1f5f9 !important;
    }

    /* Ambient Background Mesh Gradient */
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.07) 0%, transparent 40%),
                    radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.6) 0%, transparent 80%),
                    #07090e !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: rgba(13, 18, 30, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        transform: translateX(3px);
    }

    /* Modern Glassmorphic Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), 0 0 1px 1px rgba(255, 255, 255, 0.05) inset;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.35);
        box-shadow: 0 15px 35px -10px rgba(99, 102, 241, 0.15), 0 0 1px 1px rgba(99, 102, 241, 0.2) inset;
    }

    .glass-card-sm {
        background: rgba(17, 24, 39, 0.55);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
    }

    /* Executive Header Component */
    .exec-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 18px;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px -12px rgba(0, 0, 0, 0.6);
    }

    .header-title-box {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .logo-badge {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
    }

    .header-text h1 {
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .header-text p {
        font-size: 0.82rem !important;
        color: #94a3b8 !important;
        margin: 2px 0 0 0 !important;
        font-weight: 500;
    }

    .pulse-live {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 9999px;
        color: #34d399;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.6; }
    }

    /* Metric Stat Badges */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .stat-box {
        background: rgba(17, 24, 39, 0.6);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
    }

    .stat-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--accent-color, #6366f1) 0%, transparent 100%);
    }

    .stat-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 6px;
    }

    .stat-value {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        margin-bottom: 4px;
        font-family: 'JetBrains Mono', monospace;
    }

    .stat-sub {
        font-size: 0.76rem;
        color: #64748b;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    /* Modern Portal Buttons */
    .portal-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 24px;
    }

    .portal-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        color: #e2e8f0 !important;
        text-decoration: none !important;
        font-size: 0.82rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .portal-pill:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }

    /* Terminal Console */
    .terminal-container {
        background: #090d16;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem;
        color: #38bdf8;
        max-height: 400px;
        overflow-y: auto;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.7);
    }

    /* Section Subheadings */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        margin: 16px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        color: #f8fafc;
    }

    /* Buttons Overrides */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 20px !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.45) !important;
    }

    /* Primary and Secondary Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
        font-size: 0.88rem !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
    }

    /* Code blocks */
    .stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Custom Status Badges */
    .badge-success {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-warning {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-danger {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-info {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(6, 182, 212, 0.15);
        color: #06b6d4;
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_top_header():
    """Renders the executive master header with cluster heartbeat and live stats."""
    header_html = """
    <div class="exec-header">
        <div class="header-title-box">
            <div class="logo-badge">⚡</div>
            <div class="header-text">
                <h1>BDP Enterprise Platform Studio & Control Engine</h1>
                <p>Apache Spark 3.5.0 • Delta Lake 3.2.0 • Hive Metastore • YARN 3.4.0 • MinIO S3</p>
            </div>
        </div>
        <div>
            <div class="pulse-live">
                <div class="pulse-dot"></div>
                Cluster Status: Online
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def render_portal_shortcuts():
    """Renders quick-launch link pills to Hue, Jupyter, MinIO, Keycloak, Spark, YARN."""
    portals_html = """
    <div class="portal-bar">
        <a href="http://localhost:8888" target="_blank" class="portal-pill">
            <span>🎨</span> Hue Studio (8888)
        </a>
        <a href="http://localhost:8889" target="_blank" class="portal-pill">
            <span>📓</span> JupyterLab (8889)
        </a>
        <a href="http://localhost:9001" target="_blank" class="portal-pill">
            <span>🪣</span> MinIO Console (9001)
        </a>
        <a href="http://localhost:8080" target="_blank" class="portal-pill">
            <span>🔐</span> Keycloak IAM (8080)
        </a>
        <a href="http://localhost:8089" target="_blank" class="portal-pill">
            <span>⚡</span> Spark Master UI (8089)
        </a>
        <a href="http://localhost:8088" target="_blank" class="portal-pill">
            <span>🐘</span> YARN RM (8088)
        </a>
        <a href="http://localhost:4040" target="_blank" class="portal-pill">
            <span>📊</span> Spark Driver Telemetry (4040)
        </a>
        <a href="http://localhost:18080" target="_blank" class="portal-pill">
            <span>📜</span> Spark History (18080)
        </a>
    </div>
    """
    st.markdown(portals_html, unsafe_allow_html=True)

def render_hero_stats(active_workers=2, total_cores=12, total_memory="20 GB", tables_count=12, active_jobs=0):
    """Renders the 4-column executive metrics bar."""
    stats_html = f"""
    <div class="metric-grid">
        <div class="stat-box" style="--accent-color: #6366f1;">
            <div class="stat-label">Compute Capacity</div>
            <div class="stat-value">{total_cores} Cores</div>
            <div class="stat-sub">⚡ {active_workers} Active Worker Nodes</div>
        </div>
        <div class="stat-box" style="--accent-color: #06b6d4;">
            <div class="stat-label">Cluster Memory</div>
            <div class="stat-value">{total_memory}</div>
            <div class="stat-sub">🧠 Dedicated High-Speed RAM</div>
        </div>
        <div class="stat-box" style="--accent-color: #10b981;">
            <div class="stat-label">Metastore Tables</div>
            <div class="stat-value">{tables_count}</div>
            <div class="stat-sub">📦 Delta Lake & Parquet Tables</div>
        </div>
        <div class="stat-box" style="--accent-color: #f59e0b;">
            <div class="stat-label">Active Workloads</div>
            <div class="stat-value">{active_jobs} Running</div>
            <div class="stat-sub">🔄 Ingestions & SQL Pipelines</div>
        </div>
    </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)
