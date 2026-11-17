"""Tema visual Capit-in untuk Streamlit.

Warna dasar (primary, background, dll.) diatur di .streamlit/config.toml.
File ini menambahkan CSS buatan sendiri untuk komponen khusus (kartu KPI, badge,
tabel, sidebar). Panggil `apply()` sekali di awal setiap eksekusi halaman.
"""
import streamlit as st

PALETTE = {
    'primary': '#0F4C5C',
    'secondary': '#E07A3F',
    'accent': '#2A7F62',
    'positive': '#2A7F62',
    'negative': '#B3412E',
    'warning': '#C98A2B',
    'info': '#0F4C5C',
    'ink': '#1F2A2E',
    'muted': '#6B7578',
    'cream': '#F6F3EC',
    'sand': '#EFE9DC',
    'line': '#E6E1D6',
    'teal_soft': '#E3EEEE',
    'ember_soft': '#FBEADF',
    'moss_soft': '#E4F1EA',
    'rose_soft': '#F7E2DE',
}

HEX = {k: v for k, v in PALETTE.items()}

_CSS = """
/* ---------- kerangka ---------- */
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, .stAppDeployButton, [data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
section[data-testid="stSidebar"] { border-right: 1px solid var(--line); }

/* ---------- teks ---------- */
.cp-eyebrow { font-size: 10px; letter-spacing: .18em; color: var(--muted); text-transform: uppercase; }
.cp-appline { font-size: .85rem; color: var(--ink); margin-bottom: 1.4rem; }
.cp-page-title { font-size: 2rem; font-weight: 300; letter-spacing: -.02em; color: var(--ink); line-height: 1.2; }
.cp-page-sub { font-size: .85rem; color: var(--muted); margin-top: .25rem; }
.cp-section-title { font-size: 1rem; font-weight: 500; color: var(--ink); }
.cp-hint { font-size: .75rem; color: var(--muted); }

/* ---------- badge ---------- */
.cp-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.cp-badge.teal  { background: var(--teal-soft);  color: var(--primary); }
.cp-badge.ember { background: var(--ember-soft); color: var(--secondary); }
.cp-badge.moss  { background: var(--moss-soft);  color: var(--accent); }
.cp-badge.rose  { background: var(--rose-soft);  color: var(--negative); }
.cp-badge.sand  { background: var(--sand);       color: var(--ink); }

/* ---------- kartu KPI ---------- */
.cp-kpi-top { display: flex; justify-content: space-between; align-items: center; min-height: 32px; }
.cp-kpi-title { font-size: .72rem; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.cp-kpi-value { font-size: 1.6rem; font-weight: 600; letter-spacing: -.01em; color: var(--ink); margin-top: .35rem; }
.cp-kpi-hint { font-size: .75rem; color: var(--muted); margin-top: .1rem; }
.cp-kpi-icon { font-family: 'Material Symbols Rounded'; font-size: 20px; line-height: 1; font-weight: 400;
               width: 32px; height: 32px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; }
.cp-kpi-icon.teal  { background: var(--teal-soft);  color: var(--primary); }
.cp-kpi-icon.ember { background: var(--ember-soft); color: var(--secondary); }
.cp-kpi-icon.moss  { background: var(--moss-soft);  color: var(--accent); }
.cp-kpi-icon.rose  { background: var(--rose-soft);  color: var(--negative); }
.cp-kpi-icon.sand  { background: var(--sand);       color: var(--ink); }

/* ---------- tabel ---------- */
.cp-table-wrap { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: #fff; }
table.cp-table { width: 100%; border-collapse: collapse; }
table.cp-table th { background: #F9F8F6; border-bottom: 1px solid var(--line); padding: 12px 16px;
                    font-size: .72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; text-align: left; }
table.cp-table td { padding: 12px 16px; font-size: .875rem; color: var(--ink); border-bottom: 1px solid var(--line); }
table.cp-table tr:last-child td { border-bottom: 0; }
table.cp-table tbody tr:hover td { background: #FAFAF9; }
table.cp-table .cp-r { text-align: right; }
table.cp-table .cp-c { text-align: center; }
table.cp-table td.cp-empty { text-align: center; color: var(--muted); font-style: italic; padding: 24px; }
.cp-th { font-size: .72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.cp-td { font-size: .875rem; color: var(--ink); }
.cp-th.cp-r, .cp-td.cp-r { text-align: right; }
.cp-th.cp-c, .cp-td.cp-c { text-align: center; }
.cp-sep { height: 1px; background: var(--line); margin: 0; }
[class*="st-key-cp-grid"] { gap: .35rem; }
[class*="st-key-cp-card"], [class*="st-key-cp-grid"] { background: #fff; border-radius: 12px; }
div[role="dialog"] { background: #fff; }

/* ---------- sidebar ---------- */
.cp-brand { display: flex; align-items: center; gap: 12px; padding: .25rem 0 .5rem; }
.cp-brand-logo { width: 40px; height: 40px; border-radius: 8px; background: var(--teal-soft); overflow: hidden;
                 display: flex; align-items: center; justify-content: center; font-size: 22px; }
.cp-brand-logo img { width: 100%; height: 100%; object-fit: cover; }
.cp-brand-name { font-size: 1rem; font-weight: 600; color: var(--ink); }
.cp-nav-section { font-size: 10px; letter-spacing: .18em; color: var(--muted); padding: 1rem .5rem .25rem; }
.cp-user { display: flex; align-items: center; gap: 10px; padding: .5rem 0; }
.cp-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--primary); color: #fff;
             display: flex; align-items: center; justify-content: center; font-weight: 600; }
.cp-user-name { font-size: .875rem; font-weight: 500; color: var(--ink); }
.cp-user-role { font-size: .75rem; color: var(--muted); }

/* ---------- halaman login ---------- */
.cp-login-title { font-size: 1.5rem; font-weight: 300; letter-spacing: -.01em; color: var(--ink); margin: .5rem 0 .15rem; }
"""


def _vars() -> str:
    pairs = ''.join(f'--{key.replace("_", "-")}: {value};' for key, value in PALETTE.items())
    return f':root {{ {pairs} }}'


def apply() -> None:
    """Suntikkan CSS Capit-in ke halaman."""
    st.html(f'<style>{_vars()}{_CSS}</style>')
