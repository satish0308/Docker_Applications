"""
Admin Panel v2 UI Component Library
Provides modern glassmorphism, responsive cards, neon status pills, executive headers, and custom design tokens.
"""

import streamlit as st
import textwrap

def render_html(html_str, *args, **kwargs):
    """Renders HTML safely in Streamlit without markdown whitespace codeblock artifacts."""
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

def inject_v2_theme():
    """Injects the modern, luxury SaaS enterprise dark theme CSS with crystal-clear contrast."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* Global Typography & Reset */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #07090e !important;
        color: #f8fafc !important;
    }

    /* Ambient Background Mesh Gradient */
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
                    radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.10) 0%, transparent 40%),
                    radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.7) 0%, transparent 80%),
                    #07090e !important;
    }

    /* Crisp Heading & Paragraph Colors */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em !important;
    }

    p, span, li, div {
        color: #f1f5f9;
    }

    /* High-Contrast Labels & Widget Headers */
    label, .stWidgetLabel, .stWidgetLabel p, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        letter-spacing: -0.01em !important;
    }

    /* High-Contrast Captions & Subtexts */
    .stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        color: #cbd5e1 !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: rgba(13, 18, 30, 0.95) !important;
        backdrop-filter: blur(24px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
    }

    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] label p, 
    section[data-testid="stSidebar"] label span, 
    section[data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Sidebar Radio Options */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        margin-bottom: 6px !important;
        padding: 8px 14px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #e2e8f0 !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        color: #ffffff !important;
        transform: translateX(4px) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label span {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Complete Selectbox & Dropdown High-Contrast Styling */
    div[data-testid="stSelectbox"] {
        background: transparent !important;
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stSelectbox"] label p,
    div[data-testid="stSelectbox"] label span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] div[role="combobox"],
    div[data-baseweb="select"] div[aria-haspopup="listbox"] {
        background-color: #0f172a !important;
        background: #0f172a !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="select"] svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    /* BaseWeb Popover / Dropdown Menu (Open State) */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: #0d1322 !important;
        background: #0d1322 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9) !important;
    }

    li[data-baseweb="menu-item"],
    li[data-baseweb="menu-item"] * {
        background-color: transparent !important;
        color: #f8fafc !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
    }

    li[data-baseweb="menu-item"]:hover,
    li[data-baseweb="menu-item"][aria-selected="true"] {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }

    li[data-baseweb="menu-item"]:hover * {
        color: #ffffff !important;
    }

    /* MultiSelect Tags */
    span[data-baseweb="tag"] {
        background: rgba(99, 102, 241, 0.35) !important;
        border: 1px solid rgba(99, 102, 241, 0.6) !important;
        border-radius: 6px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    span[data-baseweb="tag"] span {
        color: #ffffff !important;
    }

    /* Modern Glassmorphic Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.75);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 12px 32px -10px rgba(0, 0, 0, 0.6), 0 0 1px 1px rgba(255, 255, 255, 0.08) inset;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.45);
        box-shadow: 0 16px 40px -10px rgba(99, 102, 241, 0.2), 0 0 1px 1px rgba(99, 102, 241, 0.3) inset;
    }

    .glass-card-sm {
        background: rgba(17, 24, 39, 0.65);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
    }

    /* Executive Header Component */
    .exec-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 22px 26px;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 18px;
        margin-bottom: 24px;
        box-shadow: 0 14px 40px -12px rgba(0, 0, 0, 0.7);
    }

    .header-title-box {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .logo-badge {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        box-shadow: 0 0 24px rgba(99, 102, 241, 0.5);
    }

    .header-text h1 {
        font-size: 1.55rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.025em;
        color: #ffffff !important;
    }

    .header-text p {
        font-size: 0.86rem !important;
        color: #cbd5e1 !important;
        margin: 3px 0 0 0 !important;
        font-weight: 500;
    }

    .pulse-live {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 9999px;
        color: #34d399;
        font-size: 0.80rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 12px #10b981;
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.35); opacity: 0.6; }
    }

    /* Metric Stat Badges */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .stat-box {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
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
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #cbd5e1;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .stat-value {
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        margin-bottom: 4px;
        font-family: 'JetBrains Mono', monospace;
    }

    .stat-sub {
        font-size: 0.80rem;
        color: #94a3b8;
        font-weight: 500;
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
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        color: #f8fafc !important;
        text-decoration: none !important;
        font-size: 0.84rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .portal-pill:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
    }

    /* Tabs Styling */
    div[data-baseweb="tab-list"] {
        border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
        margin-bottom: 16px !important;
    }

    button[data-baseweb="tab"] {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 10px 18px !important;
        border-bottom: 2px solid transparent !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
        background: rgba(56, 189, 248, 0.1) !important;
        border-radius: 8px 8px 0 0 !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #ffffff !important;
    }

    /* Expanders Styling */
    [data-testid="stExpander"] {
        background: rgba(17, 24, 39, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        margin-bottom: 14px !important;
    }

    [data-testid="stExpander"] summary {
        color: #f8fafc !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 12px 16px !important;
    }

    [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary p {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }

    [data-testid="stExpander"] summary:hover {
        color: #38bdf8 !important;
    }

    /* Terminal Console */
    .terminal-container {
        background: #050811;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 12px;
        padding: 16px 20px;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem;
        color: #38bdf8;
        max-height: 420px;
        overflow-y: auto;
        line-height: 1.55;
        box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.8);
    }

    /* Section Subheadings */
    .section-title {
        font-size: 1.20rem;
        font-weight: 800;
        letter-spacing: -0.015em;
        margin: 20px 0 14px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        color: #ffffff;
    }

    /* Buttons Overrides */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 0.90rem !important;
        padding: 9px 22px !important;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.35) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 22px rgba(79, 70, 229, 0.5) !important;
    }

    /* Primary and Secondary Inputs */
    .stTextInput input, .stTextArea textarea {
        background-color: #0f172a !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        font-size: 0.90rem !important;
        font-weight: 500 !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3) !important;
    }

    /* Radio & Checkbox Labels */
    div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stRadio"] label span, div[data-testid="stCheckbox"] label span {
        color: #f8fafc !important;
        font-weight: 500 !important;
    }

    /* Dataframes & Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 12px !important;
        background-color: #0b1120 !important;
    }

    /* Code blocks */
    .stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background: #090d16 !important;
    }

    .stCodeBlock pre code {
        color: #38bdf8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
    }

    /* Custom Status Badges */
    .badge-success {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(16, 185, 129, 0.18);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .badge-warning {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(245, 158, 11, 0.18);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .badge-danger {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(244, 63, 94, 0.18);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.4);
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .badge-info {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(6, 182, 212, 0.18);
        color: #38bdf8;
        border: 1px solid rgba(6, 182, 212, 0.4);
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_top_header(is_healthy=True, down_services=None):
    """Renders the executive master header with dynamic cluster heartbeat and live stats."""
    if is_healthy:
        pulse_badge = '<div class="pulse-live"><div class="pulse-dot"></div>Cluster Status: Online</div>'
    else:
        down_count = len(down_services) if down_services else 1
        down_summary = ", ".join(down_services[:2]) + ("..." if down_services and len(down_services) > 2 else "") if down_services else "Service Down"
        pulse_badge = f'<div style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; background: rgba(244, 63, 94, 0.2); border: 1px solid rgba(244, 63, 94, 0.6); border-radius: 9999px; color: #fb7185; font-size: 0.80rem; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;"><div style="width: 8px; height: 8px; border-radius: 50%; background-color: #f43f5e; box-shadow: 0 0 12px #f43f5e; animation: pulse-glow 1.2s infinite;"></div>Server Unhealthy ({down_count} Down: {down_summary})</div>'

    header_html = f'''<div class="exec-header"><div class="header-title-box"><div class="logo-badge">⚡</div><div class="header-text"><h1 style="margin:0; font-size:1.55rem; font-weight:800; color:#ffffff;">BDP Enterprise Platform Studio & Control Engine</h1><p style="margin:3px 0 0 0; color:#cbd5e1; font-size:0.86rem;">Apache Spark 3.5.0 • Delta Lake 3.2.0 • Hive Metastore • YARN 3.4.0 • MinIO S3</p></div></div><div>{pulse_badge}</div></div>'''
    st.markdown(header_html, unsafe_allow_html=True)

def render_portal_shortcuts():
    """Renders quick-launch link pills to Hue, Jupyter, MinIO, Keycloak, Spark, YARN."""
    portals_html = '''<div class="portal-bar"><a href="http://localhost:8888" target="_blank" class="portal-pill"><span>🎨</span> Hue Studio (8888)</a><a href="http://localhost:8889" target="_blank" class="portal-pill"><span>📓</span> JupyterLab (8889)</a><a href="http://localhost:9001" target="_blank" class="portal-pill"><span>🪣</span> MinIO Console (9001)</a><a href="http://localhost:8080" target="_blank" class="portal-pill"><span>🔐</span> Keycloak IAM (8080)</a><a href="http://localhost:8089" target="_blank" class="portal-pill"><span>⚡</span> Spark Master UI (8089)</a><a href="http://localhost:8088" target="_blank" class="portal-pill"><span>🐘</span> YARN RM (8088)</a><a href="http://localhost:4040" target="_blank" class="portal-pill"><span>📊</span> Spark Telemetry (4040)</a><a href="http://localhost:18080" target="_blank" class="portal-pill"><span>📜</span> Spark History (18080)</a></div>'''
    st.markdown(portals_html, unsafe_allow_html=True)

def render_hero_stats(active_workers=2, total_cores=12, total_memory="20 GB", tables_count=12, active_jobs=0):
    """Renders the 4-column executive metrics bar."""
    stats_html = f'''<div class="metric-grid"><div class="stat-box" style="--accent-color: #6366f1;"><div class="stat-label">Compute Capacity</div><div class="stat-value">{total_cores} Cores</div><div class="stat-sub">⚡ {active_workers} Active Worker Nodes</div></div><div class="stat-box" style="--accent-color: #06b6d4;"><div class="stat-label">Cluster Memory</div><div class="stat-value">{total_memory}</div><div class="stat-sub">🧠 Dedicated High-Speed RAM</div></div><div class="stat-box" style="--accent-color: #10b981;"><div class="stat-label">Metastore Tables</div><div class="stat-value">{tables_count}</div><div class="stat-sub">📦 Delta Lake & Parquet Tables</div></div><div class="stat-box" style="--accent-color: #f59e0b;"><div class="stat-label">Active Workloads</div><div class="stat-value">{active_jobs} Running</div><div class="stat-sub">🔄 Ingestions & SQL Pipelines</div></div></div>'''
    st.markdown(stats_html, unsafe_allow_html=True)
