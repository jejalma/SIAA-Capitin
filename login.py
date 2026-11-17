"""Halaman login."""
import streamlit as st

from services import ServiceError, auth
from views import layout


def render() -> None:
    _, middle, _ = st.columns([1, 1.1, 1])
    with middle:
        st.html('<div style="height:8vh"></div>')
        layout.brand()
        st.html('<div class="cp-login-title">Masuk ke Capit-in</div>'
                '<div class="cp-hint" style="margin-bottom:1rem">Sistem Informasi Akuntansi Tambak Kepiting</div>')
        with st.form('login-form', border=True):
            email = st.text_input('Email', placeholder='nama@capit.in', key='login-email')
            password = st.text_input('Kata sandi', type='password', key='login-password')
            submitted = st.form_submit_button('Masuk', type='primary', width='stretch')
        if submitted:
            try:
                user = auth.authenticate(email, password)
            except ServiceError as exc:
                st.error(str(exc), icon=':material/error:')
            else:
                layout.login_user(user)
                st.rerun()
