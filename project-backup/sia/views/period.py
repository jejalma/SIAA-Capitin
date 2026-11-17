"""Filter periode (dari-sampai) dengan pilihan cepat, versi Streamlit."""
from __future__ import annotations

from datetime import date
from typing import Callable

import streamlit as st

from services.reports import month_range
from views.fmt import tgl

_MODES = ['Bulan ini', 'Tahun ini', 'Semua', 'Kustom']


class Period:
    """Pakai:  period = Period(testid='laporan'); period.render(); lalu baca period.start / period.end.

    `start` dan `end` berupa teks ISO 'YYYY-MM-DD' atau None (artinya tanpa batas).
    Karena Streamlit menjalankan ulang halaman tiap pilihan berubah, `on_change` tidak diperlukan
    (parameter dipertahankan agar kode lama tetap bisa memanggil Period(on_change, testid)).
    """

    def __init__(self, on_change: Callable[[], None] | None = None, testid: str = 'period'):
        self.on_change, self.testid = on_change, testid

    # kunci state widget
    @property
    def _mode_key(self) -> str:
        return f'{self.testid}-mode'

    @property
    def _start_key(self) -> str:
        return f'{self.testid}-start'

    @property
    def _end_key(self) -> str:
        return f'{self.testid}-end'

    @property
    def mode(self) -> str:
        return st.session_state.get(self._mode_key) or 'Bulan ini'

    @property
    def _range(self) -> tuple[str | None, str | None]:
        today = date.today()
        mode = self.mode
        if mode == 'Tahun ini':
            return f'{today.year}-01-01', f'{today.year}-12-31'
        if mode == 'Semua':
            return None, None
        if mode == 'Kustom':
            start, end = st.session_state.get(self._start_key), st.session_state.get(self._end_key)
            return (start.isoformat() if start else None), (end.isoformat() if end else None)
        return month_range(today)

    @property
    def start(self) -> str | None:
        return self._range[0]

    @property
    def end(self) -> str | None:
        return self._range[1]

    @property
    def label(self) -> str:
        if not self.start and not self.end:
            return 'Semua periode'
        return f'Periode {tgl(self.start) if self.start else "awal"} s.d. {tgl(self.end) if self.end else "sekarang"}'

    @property
    def end_label(self) -> str:
        return f'Per {tgl(self.end)}' if self.end else 'Per hari ini'

    def render(self) -> None:
        first, last = month_range(date.today())
        with st.container(horizontal=True, vertical_alignment='bottom'):
            st.segmented_control('Periode', _MODES, default='Bulan ini', required=True,
                                 key=self._mode_key, label_visibility='collapsed')
            if self.mode == 'Kustom':
                st.date_input('Dari', value=date.fromisoformat(first), format='DD/MM/YYYY',
                              key=self._start_key, width=170)
                st.date_input('Sampai', value=date.fromisoformat(last), format='DD/MM/YYYY',
                              key=self._end_key, width=170)
