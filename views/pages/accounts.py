from nicegui import ui

from security import can
from services import accounts as acc_service
from views.components import (INPUT_PROPS, badge, card, confirm, data_table, form_dialog, icon_button, page_header,
                              run_safely)
from views.fmt import rp, rp_or_dash
from views.layout import protected

CATEGORY_TONES = {'ASET': 'teal', 'KEWAJIBAN': 'ember', 'MODAL': 'sand', 'PENDAPATAN': 'moss', 'BEBAN': 'rose'}


def balance_panel(status: dict, testid: str, compact: bool = False) -> None:
    ok = status['balanced']
    with ui.row().classes('w-full items-center gap-6 rounded-xl px-4 py-3 border ' +
                          ('border-[#2A7F62] bg-moss-soft' if ok else 'border-[#B3412E] bg-rose-soft')) \
            .props(f'data-testid={testid}'):
        ui.icon('check_circle' if ok else 'error_outline', size='26px').classes(
            'text-accent' if ok else 'text-negative')
        for label, value, key in [('Total Saldo Awal Debit', status['debit'], 'debit'),
                                  ('Total Saldo Awal Kredit', status['credit'], 'credit'),
                                  ('Selisih', status['diff'], 'diff')]:
            with ui.column().classes('gap-0'):
                ui.label(label.upper()).classes('text-[10px] tracking-[0.12em] text-muted')
                ui.label(rp(value)).classes('font-mono text-ink ' + ('text-sm' if compact else 'text-lg')).props(
                    f'data-testid={testid}-{key}')
        ui.space()
        with ui.column().classes('gap-0 items-end'):
            badge('SEIMBANG' if ok else 'TIDAK SEIMBANG', 'moss' if ok else 'rose').props(
                f'data-testid={testid}-badge')
            if not compact:
                ui.label('Saldo awal debit harus sama dengan saldo awal kredit').classes('text-xs text-muted')


class AccountsPage:
    def __init__(self, user: dict):
        self.role = user['role']
        self.mode = 'view'
        self.drafts: dict[int, float] = {}
        self.category: str | None = None

    def accounts(self) -> list[dict]:
        return acc_service.list_accounts()

    # ---------- dialog tambah/ubah ----------
    def open_form(self, record: dict | None = None) -> None:
        locked = bool(record) and bool(record['system_key'] or record['used'])
        all_accounts = self.accounts()
        fields = [
            {'key': 'category', 'label': 'Kategori', 'kind': 'select', 'options': acc_service.CATEGORIES,
             'disabled': locked},
            {'key': 'code', 'label': 'Kode akun', 'hint': 'Format X-XXXX, diawali 1 Aset, 2 Kewajiban, 3 Modal, '
                                                          '4 Pendapatan, 5 Beban', 'disabled': locked},
            {'key': 'name', 'label': 'Nama akun'},
            {'key': 'normal_balance', 'label': 'Saldo normal', 'kind': 'select', 'options': ['DEBIT', 'KREDIT'],
             'disabled': locked},
            {'key': 'opening_balance', 'label': 'Saldo awal (Rp)', 'kind': 'number', 'format': '%.0f'},
            {'key': 'description', 'label': 'Catatan (opsional)'},
        ]

        def live(values: dict) -> None:
            normal = values.get('normal_balance') or acc_service.DEFAULT_NORMAL.get(values.get('category'))
            preview = [a for a in all_accounts if not record or a['id'] != record['id']]
            preview.append({'id': -1, 'normal_balance': normal or 'DEBIT',
                            'opening_balance': float(values.get('opening_balance') or 0)})
            if values.get('category') and not values.get('normal_balance'):
                ui.label(f'Saldo normal umum untuk {values["category"]}: {normal}').classes('text-xs text-muted')
            if locked:
                ui.label('Akun inti / sudah dipakai di jurnal: kode, kategori & saldo normal dikunci.').classes(
                    'text-xs text-secondary')
            ui.label('STATUS SALDO AWAL SETELAH DISIMPAN').classes('text-[10px] tracking-[0.12em] text-muted mt-1')
            balance_panel(acc_service.opening_status(preview), 'coa-form-balance', compact=True)

        def submit(values: dict) -> None:
            if record:
                acc_service.update_account(record['id'], values)
            else:
                acc_service.create_account(values)
            self.refresh()

        form_dialog('Ubah Akun' if record else 'Tambah Akun', fields, record or {'opening_balance': 0}, submit, live)

    def ask_delete(self, record: dict) -> None:
        confirm(f'Hapus akun {record["code"]} {record["name"]}?',
                lambda: run_safely(lambda: acc_service.delete_account(record['id']), 'Akun dihapus.', self.refresh))

    # ---------- mode isi saldo awal ----------
    def start_opening(self) -> None:
        self.mode = 'opening'
        self.drafts = {a['id']: a['opening_balance'] for a in self.accounts()}
        self.refresh()

    def cancel_opening(self) -> None:
        self.mode, self.drafts = 'view', {}
        self.refresh()

    def save_opening(self) -> None:
        status = acc_service.opening_status(self.accounts(), self.drafts)

        def done():
            if not status['balanced']:
                ui.notify(f'Saldo awal tersimpan, namun belum seimbang (selisih {rp(status["diff"])}).',
                          type='warning', position='top')
            self.cancel_opening()

        run_safely(lambda: acc_service.set_opening_balances(self.drafts),
                   'Saldo awal tersimpan.' if status['balanced'] else None, done)

    def set_draft(self, account_id: int, value) -> None:
        self.drafts[account_id] = value or 0
        self.status.refresh()

    # ---------- render ----------
    def refresh(self) -> None:
        self.toolbar.refresh()
        self.status.refresh()
        self.table.refresh()

    def _toolbar(self) -> None:
        if self.mode == 'opening':
            ui.label('Mode isi saldo awal — ketik saldo pada kolom Saldo Awal').classes('text-sm text-secondary')
            ui.button('Batal', on_click=self.cancel_opening).props('flat color=grey-8 data-testid=coa-opening-cancel')
            ui.button('Simpan Saldo Awal', icon='check', on_click=self.save_opening).props(
                'unelevated color=primary data-testid=coa-opening-save')
            return
        if can(self.role, 'master.edit'):
            ui.button('Isi Saldo Awal', icon='edit_note', on_click=self.start_opening).props(
                'outline color=primary data-testid=coa-opening-mode-button')
        if can(self.role, 'master.create'):
            ui.button('Tambah', icon='add', on_click=lambda: self.open_form()).props(
                'unelevated color=primary data-testid=coa-add-button')

    def _status(self) -> None:
        balance_panel(acc_service.opening_status(self.accounts(), self.drafts if self.mode == 'opening' else None),
                      'coa-balance-status')

    def _status_cell(self, a: dict) -> None:
        if a['system_key']:
            badge('INTI', 'teal')
        elif a['used']:
            badge('TERPAKAI', 'sand')
        else:
            ui.label('-').classes('text-muted')

    def _opening_cell(self, a: dict) -> None:
        ui.number(value=self.drafts.get(a['id'], 0), min=0, format='%.0f',
                  on_change=lambda e, i=a['id']: self.set_draft(i, e.value)).props(
            f'{INPUT_PROPS} input-class=text-right data-testid=coa-opening-input-{a["code"]}').classes('w-44 ml-auto')

    def _actions_cell(self, a: dict) -> None:
        with ui.row().classes('gap-1 justify-end no-wrap'):
            if can(self.role, 'master.edit'):
                icon_button('edit', 'Ubah', lambda: self.open_form(a), f'coa-edit-{a["code"]}')
            if can(self.role, 'delete') and not a['system_key'] and not a['used']:
                icon_button('delete_outline', 'Hapus', lambda: self.ask_delete(a), f'coa-delete-{a["code"]}',
                            'negative')

    def _table(self) -> None:
        items = [a for a in self.accounts() if not self.category or a['category'] == self.category]
        editing = self.mode == 'opening'
        rows = [[a['code'], a['name'], lambda a=a: badge(a['category'], CATEGORY_TONES[a['category']]),
                 (lambda a=a: self._opening_cell(a)) if editing else rp_or_dash(a['opening_balance']),
                 a['normal_balance'], lambda a=a: self._status_cell(a),
                 (lambda a=a: self._actions_cell(a)) if not editing else ''] for a in items]
        data_table([('Kode', 'left'), ('Nama Akun', 'left'), ('Kategori', 'left'), ('Saldo Awal', 'right'),
                    ('Saldo Normal', 'left'), ('Status', 'left'), ('', 'right')], rows, 'Belum ada akun.', 'coa-table')

    def set_category(self, value: str) -> None:
        self.category = value or None
        self.table.refresh()

    def render(self) -> None:
        actions = page_header('Bagan Akun (Chart of Accounts)',
                              'Susun sendiri struktur akun dan isi saldo awalnya — status keseimbangan tampil langsung')
        with actions:
            self.toolbar = ui.refreshable(self._toolbar)
            self.toolbar()
        self.status = ui.refreshable(self._status)
        self.status()
        with card():
            ui.toggle({'': 'Semua', **{c: c.title() for c in acc_service.CATEGORIES}}, value='',
                      on_change=lambda e: self.set_category(e.value)).props(
                'no-caps unelevated toggle-color=primary color=white text-color=grey-8 data-testid=coa-category-filter')
            self.table = ui.refreshable(self._table)
            self.table()


@protected('/akun', 'Bagan Akun')
def accounts_page(user: dict) -> None:
    AccountsPage(user).render()
