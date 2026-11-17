from datetime import date

from nicegui import ui

from security import can
from services import ServiceError, accounts, master
from services import transactions as tx
from views.components import (INPUT_PROPS, badge, card, confirm, data_table, icon_button, page_header,
                              run_safely, section_title)
from views.fmt import kg, rp, tgl
from views.layout import protected
from views.pages.dashboard import type_badge

TYPE_DEFAULTS = {'PAKAN': {'qty': 5, 'unit_price': 10000}, 'GAJI': {'qty': 1}}
EMPTY = {'collector_id': None, 'product_id': None, 'employee_id': None, 'account_id': None, 'qty': None,
         'unit_price': None, 'amount': None, 'note': '', 'payment': 'kas'}


def _input(el, testid: str):
    return el.props(f'{INPUT_PROPS} data-testid={testid}').classes('w-full')


class TransactionForm:
    def __init__(self, user: dict, on_saved):
        self.user, self.on_saved = user, on_saved
        self.state = {'type': 'PENJUALAN', 'date': date.today().isoformat(), **EMPTY}

    def set(self, key: str, value) -> None:
        self.state[key] = value
        self.preview.refresh()

    def change_type(self, tx_type: str) -> None:
        self.state.update({**EMPTY, **TYPE_DEFAULTS.get(tx_type, {})}, type=tx_type)
        self.fields.refresh()
        self.preview.refresh()

    def render(self) -> None:
        with card():
            section_title('Catat Transaksi Baru', 'Jurnal debit/kredit dibuat otomatis saat disimpan')
            _input(ui.select({k: v[0] for k, v in tx.TYPES.items()}, label='Jenis Transaksi', value='PENJUALAN',
                             on_change=lambda e: self.change_type(e.value)), 'tx-type-select')
            self.fields = ui.refreshable(self._fields)
            self.fields()
            self.preview = ui.refreshable(self._preview)
            self.preview()
            ui.button('Simpan Transaksi', icon='check', on_click=self.save).props(
                'unelevated color=primary data-testid=tx-submit-button').classes('w-full')

    def _fields(self) -> None:
        s, t = self.state, self.state['type']
        bind = lambda key: (lambda e: self.set(key, e.value))  # noqa: E731
        _input(ui.date_input('Tanggal', value=s['date'], on_change=bind('date')), 'tx-date-input')
        if t in ('PENJUALAN', 'PENERIMAAN_PIUTANG'):
            collectors = master.list_collectors()
            options = {c['id']: c['name'] + (f'  ·  piutang {rp(c["receivable"])}' if c['receivable'] else '')
                       for c in collectors}
            _input(ui.select(options, label='Pengepul', value=s['collector_id'], with_input=True,
                             on_change=bind('collector_id')), 'tx-collector-select')
        if t == 'PENJUALAN':
            products = {p['id']: p for p in master.list_products()}
            price = None

            def pick_product(e):
                s['product_id'] = e.value
                if e.value:
                    price.set_value(products[e.value]['price_per_kg'])
                self.preview.refresh()

            _input(ui.select({k: f'{p["name"]}  ·  stok {kg(p["stock_kg"])}' for k, p in products.items()},
                             label='Produk Kepiting', value=s['product_id'], on_change=pick_product),
                   'tx-product-select')
            with ui.row().classes('w-full no-wrap gap-3'):
                _input(ui.number('Jumlah (kg)', value=s['qty'], min=0, step=0.5, on_change=bind('qty')), 'tx-qty-input')
                price = _input(ui.number('Harga per kg', value=s['unit_price'], min=0, format='%.0f',
                                         on_change=bind('unit_price')), 'tx-price-input')
        if t == 'PAKAN':
            with ui.row().classes('w-full no-wrap gap-3'):
                _input(ui.number('Ikan rucah (kg)', value=s['qty'], min=0, step=0.5, on_change=bind('qty')),
                       'tx-qty-input')
                _input(ui.number('Harga per kg', value=s['unit_price'], min=0, format='%.0f',
                                 on_change=bind('unit_price')), 'tx-price-input')
        if t == 'GAJI':
            employees = master.list_employees(active_only=True)
            _input(ui.select({e['id']: f'{e["name"]}  ·  {rp(e["daily_wage"])}/hari' for e in employees},
                             label='Karyawan', value=s['employee_id'], on_change=bind('employee_id')),
                   'tx-employee-select')
            _input(ui.number('Jumlah hari kerja', value=s['qty'], min=0, step=1, format='%.0f', on_change=bind('qty')),
                   'tx-qty-input')
        if t == 'OPERASIONAL':
            options = {a['id']: f'{a["code"]} · {a["name"]}' for a in accounts.list_accounts('BEBAN')}
            _input(ui.select(options, label='Akun Beban', value=s['account_id'], on_change=bind('account_id')),
                   'tx-account-select')
        if t in ('OPERASIONAL', 'MODAL', 'PRIVE', 'PENERIMAAN_PIUTANG'):
            _input(ui.number('Nominal (Rp)', value=s['amount'], min=0, format='%.0f', on_change=bind('amount')),
                   'tx-amount-input')
        payments = {k: v for k, v in tx.PAYMENTS.items() if k != 'piutang' or t == 'PENJUALAN'}
        _input(ui.select(payments, label='Kas / Bank' if t != 'PENJUALAN' else 'Metode Pembayaran',
                         value=s['payment'], on_change=bind('payment')), 'tx-payment-select')
        _input(ui.input('Keterangan (opsional)', value=s['note'], on_change=bind('note')), 'tx-note-input')

    def _preview(self) -> None:
        with ui.column().classes('w-full gap-2 rounded-lg bg-cream p-4').props('data-testid=tx-preview'):
            try:
                draft = tx.preview(self.state['type'], self.state)
            except ServiceError as exc:
                ui.label('Pratinjau Jurnal').classes('text-[10px] tracking-[0.15em] text-muted')
                ui.label(str(exc)).classes('text-sm text-muted').props('data-testid=tx-preview-message')
                return
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('PRATINJAU JURNAL').classes('text-[10px] tracking-[0.15em] text-muted')
                badge('SEIMBANG', 'moss')
            ui.label(rp(draft['amount'])).classes('text-2xl font-mono text-ink').props('data-testid=tx-preview-total')
            for line in draft['lines']:
                is_debit = line['debit'] > 0
                with ui.row().classes('w-full no-wrap items-center text-sm' + ('' if is_debit else ' pl-6')):
                    ui.label(f'{line["code"]}  {line["name"]}').classes('text-ink')
                    ui.space()
                    ui.label(('Dr ' if is_debit else 'Cr ') + rp(line['debit'] or line['credit'])).classes(
                        'font-mono ' + ('text-primary' if is_debit else 'text-secondary'))

    def save(self) -> None:
        def action():
            result = tx.record(self.state['type'], self.state, self.user['id'])
            ui.notify(f'Transaksi {result["ref_no"]} tersimpan dan dijurnal.', type='positive', position='top')

        if run_safely(action):
            self.state.update({**EMPTY, **TYPE_DEFAULTS.get(self.state['type'], {})})
            self.fields.refresh()
            self.preview.refresh()
            self.on_saved()


class TransactionList:
    def __init__(self, user: dict):
        self.user = user
        self.filters = {'type': None, 'start': None, 'end': None, 'search': ''}

    def set(self, key: str, value) -> None:
        self.filters[key] = value or None
        self.table.refresh()

    def render(self) -> None:
        with card():
            section_title('Daftar Transaksi')
            with ui.row().classes('w-full gap-3 no-wrap'):
                _input(ui.select({'': 'Semua jenis', **{k: v[0] for k, v in tx.TYPES.items()}}, value='',
                                 label='Jenis', on_change=lambda e: self.set('type', e.value)), 'tx-filter-type')
                _input(ui.date_input('Dari', on_change=lambda e: self.set('start', e.value)), 'tx-filter-start')
                _input(ui.date_input('Sampai', on_change=lambda e: self.set('end', e.value)), 'tx-filter-end')
            _input(ui.input('Cari keterangan / no. ref', on_change=lambda e: self.set('search', e.value)).props(
                'clearable debounce=300'), 'tx-filter-search')
            self.table = ui.refreshable(self._table)
            self.table()

    def _table(self) -> None:
        allow_delete = can(self.user['role'], 'delete')
        items = tx.list_transactions(self.filters['type'], self.filters['start'], self.filters['end'],
                                     self.filters['search'])
        headers = [('Tanggal', 'left'), ('No. Ref', 'left'), ('Jenis', 'left'), ('Keterangan', 'left'),
                   ('Nilai', 'right')] + ([('', 'right')] if allow_delete else [])
        rows = []
        for t in items:
            cells = [tgl(t['date']), t['ref_no'], lambda t=t: type_badge(t['type']), t['description'], rp(t['amount'])]
            if allow_delete:
                cells.append(lambda t=t: icon_button('delete_outline', 'Hapus transaksi', lambda: self.ask_delete(t),
                                                     f'tx-delete-{t["id"]}', 'negative'))
            rows.append(cells)
        ui.label(f'{len(items)} transaksi · total {rp(sum(t["amount"] for t in items))}').classes(
            'text-xs text-muted').props('data-testid=tx-list-summary')
        data_table(headers, rows, 'Belum ada transaksi.', 'tx-table')

    def ask_delete(self, t: dict) -> None:
        confirm(f'Hapus transaksi {t["ref_no"]}? Jurnal dan pergerakan stoknya ikut terhapus.',
                lambda: run_safely(lambda: tx.delete_transaction(t['id']), 'Transaksi dihapus.', self.table.refresh))


@protected('/transaksi', 'Transaksi')
def transactions_page(user: dict) -> None:
    page_header('Transaksi', 'Penjualan kepiting, pakan, gaji, beban operasional, modal & prive')
    tx_list = TransactionList(user)
    with ui.grid().classes('w-full grid-cols-1 xl:grid-cols-12 gap-4 items-start'):
        with ui.column().classes('xl:col-span-5 w-full'):
            TransactionForm(user, lambda: tx_list.table.refresh()).render()
        with ui.column().classes('xl:col-span-7 w-full'):
            tx_list.render()
