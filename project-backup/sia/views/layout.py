"""Kerangka aplikasi (sidebar, navigasi, hak akses) versi Streamlit.

Halaman didaftarkan dengan dekorator `@protected(path, title, permission)` persis seperti
versi NiceGUI; fungsi yang didekorasi menerima `user` dan menggambar isi halaman dengan
perintah Streamlit (`st.*`). `run(user)` lalu membangun navigasi dari daftar NAV.
"""
from __future__ import annotations

import base64
import importlib
import inspect
import sys
from functools import lru_cache
from pathlib import Path

import streamlit as st

from security import ROLE_LABELS, can
from services import auth
from views import components

NAV = [
    (None, [
        ('/', 'Dashboard', 'dashboard', None),
        ('/transaksi', 'Transaksi', 'receipt_long', None),
        ('/jurnal', 'Jurnal & Buku Besar', 'menu_book', None),
        ('/laporan', 'Laporan Keuangan', 'bar_chart', None),
    ]),
    ('MASTER DATA', [
        ('/produk', 'Produk Kepiting', 'set_meal', None),
        ('/pengepul', 'Pengepul', 'groups', None),
        ('/karyawan', 'Karyawan', 'badge', None),
        ('/akun', 'Bagan Akun', 'account_tree', None),
        ('/stok', 'Stok Kepiting', 'inventory_2', None),
    ]),
    ('SISTEM', [
        ('/pengguna', 'Pengguna', 'admin_panel_settings', 'users.manage'),
    ]),
]

APP_LINE = 'Capit-in · Sistem Informasi Akuntansi Tambak Kepiting'
LOGO_PATH = Path(__file__).resolve().parent.parent / 'static' / 'logo.png'

PAGES: dict[str, dict] = {}          # path -> {title, permission, builder, legacy}
IMPORT_ERRORS: dict[str, str] = {}   # modul halaman yang gagal di-import
_LOADED: set[str] = set()


# ---------- sesi pengguna ----------
def current_user() -> dict | None:
    return auth.get_user(st.session_state.get('uid'))


def login_user(user: dict) -> None:
    st.session_state['uid'] = user['id']


def logout() -> None:
    st.session_state.clear()


# ---------- pendaftaran halaman ----------
def _uses_nicegui(builder) -> bool:
    try:
        source = inspect.getsourcefile(builder)
        return bool(source) and 'nicegui' in Path(source).read_text(encoding='utf-8')
    except (OSError, TypeError):
        return False


def protected(path: str, title: str, permission: str | None = None):
    """Daftarkan fungsi `builder(user)` sebagai halaman di alamat `path`."""
    def decorator(builder):
        PAGES[path] = {'title': title, 'permission': permission, 'builder': builder,
                       'legacy': _uses_nicegui(builder)}
        return builder
    return decorator


def load_page_module(name: str) -> None:
    """Import modul views.pages.<name> agar dekorator @protected-nya terdaftar."""
    full = f'views.pages.{name}'
    if full in _LOADED:
        return
    try:
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)
    except Exception as exc:  # noqa: BLE001 - halaman lama (NiceGUI) bisa gagal di-import
        IMPORT_ERRORS[name] = f'{type(exc).__name__}: {exc}'
        return
    IMPORT_ERRORS.pop(name, None)
    _LOADED.add(full)


# ---------- tampilan ----------
@lru_cache(maxsize=1)
def _logo_html() -> str:
    if LOGO_PATH.exists():
        data = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{data}" alt="logo">'
    return '🦀'


def brand() -> None:
    st.html(f'<div class="cp-brand"><div class="cp-brand-logo">{_logo_html()}</div>'
            '<div><div class="cp-eyebrow">SIA TAMBAK KEPITING</div>'
            '<div class="cp-brand-name">Capit-in</div></div></div>')


def _sidebar(user: dict, pages: dict[str, st.Page]) -> None:
    with st.sidebar:
        brand()
        for section, items in NAV:
            visible = [item for item in items if item[0] in pages]
            if not visible:
                continue
            if section:
                st.html(f'<div class="cp-nav-section">{section}</div>')
            for path, label, icon, _ in visible:
                st.page_link(pages[path], label=label, icon=f':material/{icon}:', width='stretch')
        st.divider()
        st.html(f'<div class="cp-user"><div class="cp-avatar">{components.esc(user["name"][:1].upper())}</div>'
                f'<div><div class="cp-user-name">{components.esc(user["name"])}</div>'
                f'<div class="cp-user-role">{components.esc(ROLE_LABELS[user["role"]])}</div></div></div>')
        st.button('Keluar', icon=':material/logout:', key='logout-button', on_click=logout, width='stretch')


def _runner(path: str, info: dict, user: dict):
    def run() -> None:
        components.begin_page()
        st.html(f'<div class="cp-eyebrow">{components.esc(info["title"].upper())}</div>'
                f'<div class="cp-appline">{APP_LINE}</div>')
        builder = info.get('builder')
        if builder is None or info.get('legacy'):
            st.warning(f'Halaman "{info["title"]}" belum dikonversi ke Streamlit.', icon=':material/construction:')
            module_errors = [f'{name}: {err}' for name, err in IMPORT_ERRORS.items()]
            if module_errors:
                with st.expander('Detail'):
                    st.code('\n'.join(module_errors))
            return
        builder(user)

    run.__name__ = 'page_' + (path.strip('/').replace('-', '_') or 'dashboard')
    return run


def _allowed(user: dict, permission: str | None) -> bool:
    return not permission or can(user['role'], permission)


def run(user: dict) -> None:
    """Bangun navigasi sesuai hak akses lalu jalankan halaman yang sedang dipilih."""
    pages: dict[str, st.Page] = {}
    for _, items in NAV:
        for path, label, icon, permission in items:
            info = PAGES.get(path) or {'title': label, 'permission': permission, 'builder': None, 'legacy': False}
            if not (_allowed(user, permission) and _allowed(user, info['permission'])):
                continue
            pages[path] = st.Page(_runner(path, {**info, 'title': label}, user), title=label,
                                  icon=f':material/{icon}:', url_path=path.strip('/'), default=(path == '/'))
    for path, info in PAGES.items():  # halaman terdaftar yang tidak ada di menu
        if path not in pages and _allowed(user, info['permission']):
            pages[path] = st.Page(_runner(path, info, user), title=info['title'], url_path=path.strip('/'))
    nav = st.navigation(list(pages.values()), position='hidden')
    _sidebar(user, pages)
    nav.run()
