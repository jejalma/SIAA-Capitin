from datetime import date

from nicegui import ui

from security import can
from services import master, stock
from views.components import (INPUT_PROPS, badge, card, confirm, data_table, icon_button, page_header,
                              run_safely, section_title)
from views.fmt import kg, rp, tgl
from views.layout import protected


class StockPage:
    def __init__(self, user: dict):
        self.user = user
        self.form = {'product_id': None, 'kind': 'PANEN', 'date': date.today().isoformat(), 'qty': None, 'note': ''}
        self.filter_product: int | None = None

    def refresh(self) -> None:
        self.summary.refresh()
        self.history.refresh()

    def _summary(self) -> None:
        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-3 gap-4'):
            for p in master.list_products():
                with card('gap-1'):
                    ui.label(p['name']).classes('text-sm text-muted')
                    ui.label(kg(p['stock_kg'])).classes('text-2xl font-mono text-ink').props(
                        f'data-testid=stock-kg-{p["id"]}')
                    ui.label(f'Nilai {rp(p["stock_value"])} · {rp(p["price_per_kg"])}/kg').classes('text-xs text-muted')

    def save(self) -> None:
        f = self.form
        if run_safely(lambda: stock.add_movement(f['product_id'], f['date'], f['kind'], f['qty'], f['note'],
                                                 self.user['id']), 'Pergerakan stok tersimpan.'):
            f.update(qty=None, note='')
            self.qty_input.set_value(None)
            self.note_input.set_value('')
            self.refresh()

    def _form(self) -> None:
        f = self.form
        with card():
            section_title('Catat Stok', 'Hasil panen (masuk), kepiting mati/susut, atau koreksi')
            products = {p['id']: p['name'] for p in master.list_products()}
            ui.select(products, label='Produk', value=f['product_id'],
                      on_change=lambda e: f.update(product_id=e.value)).props(
                f'{INPUT_PROPS} data-testid=stock-product-select').classes('w-full')
            ui.select({k: v[0] for k, v in stock.KINDS.items()}, label='Jenis', value=f['kind'],
                      on_change=lambda e: f.update(kind=e.value)).props(
                f'{INPUT_PROPS} data-testid=stock-kind-select').classes('w-full')
            with ui.row().classes('w-full no-wrap gap-3'):
                ui.date_input('Tanggal', value=f['date'], on_change=lambda e: f.update(date=e.value)).props(
                    f'{INPUT_PROPS} data-testid=stock-date-input').classes('w-full')
                self.qty_input = ui.number('Jumlah (kg)', min=0, step=0.5,
                                           on_change=lambda e: f.update(qty=e.value)).props(
                    f'{INPUT_PROPS} data-testid=stock-qty-input').classes('w-full')
            self.note_input = ui.input('Catatan (opsional)', on_change=lambda e: f.update(note=e.value)).props(
                f'{INPUT_PROPS} data-testid=stock-note-input').classes('w-full')
            ui.button('Simpan', icon='check', on_click=self.save).props(
                'unelevated color=primary data-testid=stock-submit-button').classes('w-full')

    def ask_delete(self, m: dict) -> None:
        confirm(f'Hapus catatan stok {m["product_name"]} {kg(m["qty_kg"])}?',
                lambda: run_safely(lambda: stock.delete_movement(m['id']), 'Catatan stok dihapus.', self.refresh))

    def _history(self) -> None:
        allow_delete = can(self.user['role'], 'delete')
        rows = []
        for m in stock.list_movements(self.filter_product):
            delete = (lambda m=m: icon_button('delete_outline', 'Hapus', lambda: self.ask_delete(m),
                                              f'stock-delete-{m["id"]}', 'negative')) \
                if allow_delete and not m['transaction_id'] else ''
            rows.append([tgl(m['date']), m['product_name'],
                         lambda m=m: badge(stock.KIND_LABELS.get(m['kind'], m['kind']),
                                           'moss' if m['qty_kg'] > 0 else 'ember'),
                         ('+' if m['qty_kg'] > 0 else '') + kg(m['qty_kg']), m['note'] or '-', delete])
        data_table([('Tanggal', 'left'), ('Produk', 'left'), ('Jenis', 'left'), ('Jumlah', 'right'),
                    ('Catatan', 'left'), ('', 'right')], rows, 'Belum ada pergerakan stok.', 'stock-history-table')

    def set_filter(self, value) -> None:
        self.filter_product = value or None
        self.history.refresh()

    def render(self) -> None:
        page_header('Stok Kepiting', 'Stok berkurang otomatis saat penjualan; penjualan ditolak bila stok kurang')
        self.summary = ui.refreshable(self._summary)
        self.summary()
        with ui.grid().classes('w-full grid-cols-1 xl:grid-cols-12 gap-4 items-start'):
            with ui.column().classes('xl:col-span-4 w-full'):
                if can(self.user['role'], 'stock.create'):
                    self._form()
            with ui.column().classes('xl:col-span-8 w-full'), card():
                with ui.row().classes('w-full items-center justify-between'):
                    section_title('Riwayat Pergerakan Stok')
                    ui.select({'': 'Semua produk', **{p['id']: p['name'] for p in master.list_products()}}, value='',
                              on_change=lambda e: self.set_filter(e.value)).props(
                        f'{INPUT_PROPS} data-testid=stock-filter-product').classes('w-56')
                self.history = ui.refreshable(self._history)
                self.history()


@protected('/stok', 'Stok Kepiting')
def stock_page(user: dict) -> None:
    StockPage(user).render()
