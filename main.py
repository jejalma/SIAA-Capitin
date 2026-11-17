"""Titik masuk aplikasi Capit-in (Streamlit).

Jalankan dari folder proyek:
    streamlit run main.py
"""
import streamlit as st

import config
import database
from views import layout, theme
from views.pages import login

st.set_page_config(
    page_title=f'{config.APP_NAME} · SIA Tambak Kepiting',
    page_icon='🦀',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Modul halaman yang mendaftarkan diri lewat @protected (isi views/pages/).
PAGE_MODULES = ['dashboard', 'transactions', 'journal', 'reports', 'master_data', 'accounts', 'stock']


@st.cache_resource(show_spinner=False)
def _init_db() -> bool:
    """Buat tabel + data awal sekali per proses server."""
    database.init_db()
    return True


_init_db()
theme.apply()

user = layout.current_user()
if not user:
    login.render()
    st.stop()

for name in PAGE_MODULES:
    layout.load_page_module(name)
layout.run(user)
