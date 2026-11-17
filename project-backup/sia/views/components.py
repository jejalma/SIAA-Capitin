"""Komponen UI Capit-in versi Streamlit.

Nama dan parameter fungsi dipertahankan dari versi NiceGUI supaya halaman lain
cukup disesuaikan seperlunya. Perbedaan penting cara kerja Streamlit:

* Streamlit menjalankan ulang skrip setiap ada interaksi, jadi tidak ada
  `table.refresh()`. Setelah data berubah, cukup panggil `st.rerun()`.
* Dialog (form tambah/ubah, konfirmasi) memakai `st.dialog`.
* Pesan sukses disimpan lewat `notify()` lalu ditampilkan oleh `show_flash()`
  pada eksekusi berikutnya, supaya tidak hilang saat `st.rerun()`.
"""
from __future__ import annotations

import html
from datetime import date
from itertools import count
from typing import Callable

import streamlit as st

from services import ServiceError
from services.pdf import table_pdf

TONES = ('teal', 'ember', 'moss', 'rose', 'sand')
INPUT_PROPS = 'outlined dense'  # sisa NiceGUI; dipertahankan agar import lama tidak error

_dialog_ids = count(1)
_ICON_ALIASES = {'delete_outline': 'delete'}
_FLASH_ICONS = {'positive': '✅', 'negative': '⚠️', 'warning': '⚠️', 'info': 'ℹ️'}


def esc(value) -> str:
    return html.escape(str(value))


# ---------- pesan ----------
def notify(message: str, type: str = 'positive') -> None:
    """Antrekan pesan; akan tampil sebagai toast pada eksekusi berikutnya."""
    st.session_state.setdefault('_flash', []).append((type, message))


def show_flash() -> None:
    for kind, message in st.session_state.pop('_flash', []):
        st.toast(message, icon=_FLASH_ICONS.get(kind))


def begin_page() -> None:
    """Dipanggil layout di awal tiap halaman (reset penghitung kunci, tampilkan pesan)."""
    st.session_state['_tbl_counts'] = {}
    st.session_state['_card_n'] = 0
    show_flash()


def run_safely(action: Callable, success: str | None = None, after: Callable | None = None) -> bool:
    """Jalankan `action`. ServiceError ditampilkan sebagai pesan error (return False).

    Jika berhasil: pesan `success` diantrekan lalu `after()` dipanggil
    (biasanya `st.rerun`). Tanpa `after`, pesan langsung tampil sebagai toast.
    """
    try:
        action()
    except ServiceError as exc:
        st.error(str(exc), icon=':material/error:')
        return False
    if success:
        if after:
            notify(success)
        else:
            st.toast(success, icon=_FLASH_ICONS['positive'])
    if after:
        after()
    return True


# ---------- elemen dasar ----------
def page_header(title: str, subtitle: str | None = None):
    """Judul halaman. Mengembalikan wadah di kanan untuk tombol aksi: `with actions: st.button(...)`."""
    left, right = st.columns([3, 2], vertical_alignment='bottom')
    with left:
        sub = f'<div class="cp-page-sub">{esc(subtitle)}</div>' if subtitle else ''
        st.html(f'<div class="cp-page-title">{esc(title)}</div>{sub}')
    return right.container(horizontal=True, horizontal_alignment='right')


def card(extra: str = ''):
    """Kartu putih berbingkai. Pakai: `with card(): ...` (parameter `extra` diabaikan)."""
    st.session_state['_card_n'] = st.session_state.get('_card_n', 0) + 1
    return st.container(border=True, key=f'cp-card-{st.session_state["_card_n"]}')


def section_title(title: str, hint: str | None = None) -> None:
    hint_html = f'<div class="cp-hint">{esc(hint)}</div>' if hint else ''
    st.html(f'<div class="cp-section-title">{esc(title)}</div>{hint_html}')


def badge_html(text: str, tone: str = 'teal') -> str:
    tone = tone if tone in TONES else 'teal'
    return f'<span class="cp-badge {tone}">{esc(text)}</span>'


def badge(text: str, tone: str = 'teal') -> None:
    st.html(badge_html(text, tone))


def kpi(title: str, value, hint: str | None = None, icon: str | None = None,
        tone: str = 'teal', test_id: str | None = None) -> None:
    """Kotak statistik untuk dashboard. `icon` = nama ikon Material (mis. 'trending_up').

    Letakkan di dalam `st.columns(...)` agar berjajar.
    """
    tone = tone if tone in TONES else 'teal'
    corner = f'<span class="cp-kpi-icon {tone}">{esc(icon)}</span>' if icon else badge_html(tone.capitalize(), tone)
    hint_html = f'<div class="cp-kpi-hint">{esc(hint)}</div>' if hint else ''
    with card():
        st.html(f'<div class="cp-kpi-top"><span class="cp-kpi-title">{esc(title)}</span>{corner}</div>'
                f'<div class="cp-kpi-value">{esc(value)}</div>{hint_html}')


def icon_button(icon: str, tooltip: str, on_click: Callable, testid: str, color: str = 'grey-8') -> None:
    """Tombol ikon kecil. `testid` dipakai sebagai key (harus unik di halaman)."""
    name = _ICON_ALIASES.get(icon, icon)
    if st.button(' ', icon=f':material/{name}:', help=tooltip, key=testid, type='tertiary'):
        on_click()


# ---------- tabel ----------
def _align_class(align: str) -> str:
    return {'right': 'cp-r', 'center': 'cp-c'}.get(align, '')


def _static_table(headers: list[tuple[str, str]], rows: list[list], empty_text: str) -> None:
    head = ''.join(f'<th class="{_align_class(a)}">{esc(h)}</th>' for h, a in headers)
    if rows:
        body = ''.join(
            '<tr>' + ''.join(f'<td class="{_align_class(headers[i][1])}">{esc(c)}</td>'
                             for i, c in enumerate(row)) + '</tr>'
            for row in rows)
    else:
        body = f'<tr><td class="cp-empty" colspan="{len(headers)}">{esc(empty_text)}</td></tr>'
    st.html(f'<div class="cp-table-wrap"><table class="cp-table"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _grid_table(headers: list[tuple[str, str]], rows: list[list], testid: str, widths: list[float] | None) -> None:
    counts = st.session_state.setdefault('_tbl_counts', {})
    counts[testid] = counts.get(testid, 0) + 1
    widths = widths or [1] * len(headers)
    with st.container(border=True, key=f'cp-grid-{testid}-{counts[testid]}'):
        head = st.columns(widths, vertical_alignment='center')
        for col, (name, align) in zip(head, headers):
            col.html(f'<div class="cp-th {_align_class(align)}">{esc(name)}</div>')
        for row in rows:
            st.html('<div class="cp-sep"></div>')
            cols = st.columns(widths, vertical_alignment='center')
            for col, cell, (_, align) in zip(cols, row, headers):
                with col:
                    if callable(cell):
                        cell()  # sel berupa fungsi (badge, tombol aksi): jalankan
                    else:
                        st.html(f'<div class="cp-td {_align_class(align)}">{esc(cell)}</div>')


def data_table(headers: list[tuple[str, str]], rows: list[list],
               empty_text: str = 'Tidak ada data tersedia.', testid: str = 'table',
               widths: list[float] | None = None) -> None:
    """Tabel data. `headers` = [(judul, 'left'|'right'|'center')]. Sel boleh berupa fungsi (tombol/badge).

    Tanpa sel fungsi, tabel dirender sebagai HTML biasa (cepat). Dengan sel fungsi, dirender
    per baris memakai kolom Streamlit; `widths` mengatur lebar relatif tiap kolom.
    """
    interactive = any(callable(cell) for row in rows for cell in row)
    if rows and interactive:
        _grid_table(headers, rows, testid, widths)
    else:
        _static_table(headers, rows, empty_text)


# ---------- laporan PDF ----------
def report_block(*, title: str, subtitle: str, headers: list[tuple[str, str]], rows: list[tuple[list, str]],
                 widths: list[float], filename: str, testid: str, orientation: str = 'P') -> None:
    pdf = table_pdf(title, subtitle, [h for h, _ in headers], rows, widths,
                    ''.join({'left': 'L', 'right': 'R', 'center': 'C'}[a] for _, a in headers), orientation)
    left, right = st.columns([4, 1], vertical_alignment='center')
    with left:
        section_title(title, subtitle)
    with right:
        st.download_button('Unduh PDF', pdf, file_name=filename, mime='application/pdf',
                           icon=':material/print:', key=f'{testid}-pdf-button', width='stretch')


# ---------- dialog ----------
def confirm(message: str, on_confirm: Callable, label: str = 'Ya, hapus') -> None:
    """Dialog konfirmasi. Panggil di eksekusi yang sama dengan klik tombol pemicunya.

    `on_confirm` boleh mengembalikan False (mis. dari run_safely) agar dialog tetap terbuka.
    """
    @st.dialog('Konfirmasi')
    def _dialog():
        st.write(message)
        cancel, yes = st.columns(2)
        if cancel.button('Batal', key='confirm-cancel-button', width='stretch'):
            st.rerun()
        if yes.button(label, key='confirm-yes-button', type='primary', width='stretch'):
            if on_confirm() is not False:
                st.rerun()

    _dialog()


def _to_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def field(spec: dict, values: dict, on_change: Callable | None = None, prefix: str = 'f'):
    """Satu input form. Nilainya ditulis ke `values[spec['key']]` dan dikembalikan.

    kind: text (default) | number | select | switch | date | password
    (`on_change` tidak dipakai di Streamlit; ada hanya demi kompatibilitas.)
    """
    key, label, kind = spec['key'], spec['label'], spec.get('kind', 'text')
    wkey = f'{prefix}-field-{key}'
    current = values.get(key)
    common = {'key': wkey, 'help': spec.get('hint'), 'disabled': bool(spec.get('disabled'))}

    if kind == 'number':
        minimum = spec.get('min', 0)
        value = st.number_input(
            label, value=None if current in (None, '') else float(current),
            min_value=None if minimum is None else float(minimum),
            step=float(spec.get('step', 1)), format=spec.get('format'), **common)
    elif kind == 'select':
        options = spec['options']
        keys = list(options)
        labels = options if isinstance(options, dict) else {k: str(k) for k in keys}
        value = st.selectbox(label, keys, index=keys.index(current) if current in keys else None,
                             format_func=lambda k: labels[k], placeholder='Pilih...', **common)
    elif kind == 'switch':
        value = st.toggle(label, value=bool(current), **common)
    elif kind == 'date':
        picked = st.date_input(label, value=_to_date(current), format='DD/MM/YYYY', **common)
        value = picked.isoformat() if picked else ''
    elif kind == 'password':
        value = st.text_input(label, type='password', **common)
    else:
        value = st.text_input(label, value=current or '', **common)
    values[key] = value
    return value


def form_dialog(title: str, fields: list[dict], initial: dict, on_submit: Callable[[dict], None],
                live: Callable[[dict], None] | None = None) -> None:
    """Dialog form tambah/ubah. Panggil di eksekusi yang sama dengan klik tombol pemicunya."""
    uid = f'dlg{next(_dialog_ids)}'
    snapshot = dict(initial)

    @st.dialog(title)
    def _dialog():
        values = dict(snapshot)
        for spec in fields:
            field(spec, values, prefix=uid)
        if live:
            live(values)
        cancel, save = st.columns(2)
        if cancel.button('Batal', key=f'{uid}-cancel', width='stretch'):
            st.rerun()
        if save.button('Simpan', icon=':material/check:', key=f'{uid}-submit', type='primary', width='stretch'):
            run_safely(lambda: on_submit(values), 'Data berhasil disimpan.', st.rerun)

    _dialog()
