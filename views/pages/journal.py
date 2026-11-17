from datetime import date

from nicegui import ui

from security import can
from services import accounts, journal, reports
from views.components import (INPUT_PROPS, badge, card, confirm, data_table, icon_button, page_header,
                              report_block, run_safely, section_title)
from views.fmt import rp, rp_or_dash, tgl
from views.layout import protected
from views.period import Period

INDENT = '\u2003\u2003'


def _journal_rows(data: dict) -> list:
    rows = []
    for entry in data['entries']:
        for i, ln in enumerate(entry['lines']):
            name = f'{ln["code"]} {ln["name"]}'
            rows.append(([tgl(entry['date']) if i == 0 else '', entry['ref_no'] if i == 0 else '',
                          name if ln['debit'] else INDENT + name, rp_or_dash(ln['debit']),
                          rp_or_dash(ln['credit'])], ''))
        rows.append((['', '', f'({entry["description"]})', '', ''], 'muted'))
    rows.append((['', '', 'TOTAL', rp(data['total_debit']), rp(data['total_credit'])], 'bold'))
    return rows


def general_journal_tab(period: Period) -> None:
    data = reports.general_journal(period.start, period.end)
    with ui.row().classes('items-center gap-2'):
        badge('SEIMBANG' if data['balanced'] else 'TIDAK SEIMBANG', 'moss' if data['balanced'] else 'rose')
        ui.label(f'{len(data["entries"])} jurnal').classes('text-xs text-muted')
    report_block(title='Jurnal Umum', subtitle=period.label,
                 headers=[('Tanggal', 'left'), ('No. Ref', 'left'), ('Akun', 'left'), ('Debit', 'right'),
                          ('Kredit', 'right')],
                 rows=_journal_rows(data), widths=[14, 13, 43, 15, 15], filename='jurnal-umum.pdf',
                 testid='general-journal')


def ledger_tab(period: Period, state: dict) -> None:
    options = {a['id']: f'{a["code"]} · {a["name"]}' for a in accounts.list_accounts()}
    state.setdefault('account_id', next(iter(options), None))

    def pick(e):
        state['account_id'] = e.value
        body.refresh()

    ui.select(options, label='Pilih Akun', value=state['account_id'], with_input=True, on_change=pick).props(
        f'{INPUT_PROPS} data-testid=ledger-account-select').classes('w-full md:w-96')

    @ui.refreshable
    def body():
        if not state['account_id']:
            return
        data = reports.ledger(state['account_id'], period.start, period.end)
        acc = data['account']
        rows = [(['', '', 'Saldo Awal', '', '', rp(data['opening'])], 'section')]
        rows += [([tgl(r['date']), r['ref_no'], r['description'], rp_or_dash(r['debit']), rp_or_dash(r['credit']),
                   rp(r['balance'])], '') for r in data['rows']]
        rows.append((['', '', 'Saldo Akhir', rp(data['total_debit']), rp(data['total_credit']), rp(data['closing'])],
                     'bold'))
        report_block(title=f'Buku Besar {acc["code"]} {acc["name"]}',
                     subtitle=f'{period.label} · Saldo normal {acc["normal_balance"]}',
                     headers=[('Tanggal', 'left'), ('No. Ref', 'left'), ('Keterangan', 'left'), ('Debit', 'right'),
                              ('Kredit', 'right'), ('Saldo', 'right')],
                     rows=rows, widths=[12, 11, 35, 14, 14, 14], filename=f'buku-besar-{acc["code"]}.pdf',
                     testid='ledger')

    body()


def trial_balance_tab(period: Period) -> None:
    data = reports.trial_balance(period.end)
    rows = [([r['code'], r['name'], rp_or_dash(r['debit']), rp_or_dash(r['credit'])], '') for r in data['rows']]
    rows.append((['', 'TOTAL', rp(data['total_debit']), rp(data['total_credit'])], 'bold'))
    badge('SEIMBANG' if data['balanced'] else 'TIDAK SEIMBANG', 'moss' if data['balanced'] else 'rose')
    report_block(title='Neraca Saldo', subtitle=period.end_label,
                 headers=[('Kode', 'left'), ('Nama Akun', 'left'), ('Debit', 'right'), ('Kredit', 'right')],
                 rows=rows, widths=[12, 48, 20, 20], filename='neraca-saldo.pdf', testid='trial-balance')


class ManualJournal:
    def __init__(self, user: dict, on_saved):
        self.user, self.on_saved = user, on_saved
        self.options = {a['id']: f'{a["code"]} · {a["name"]}' for a in accounts.list_accounts()}
        self.reset()

    def reset(self) -> None:
        self.state = {'date': date.today().isoformat(), 'description': ''}
        self.lines = [{'account_id': None, 'debit': None, 'credit': None} for _ in range(2)]

    def totals(self) -> tuple[float, float]:
        return (round(sum(ln['debit'] or 0 for ln in self.lines), 2),
                round(sum(ln['credit'] or 0 for ln in self.lines), 2))

    def render(self) -> None:
        with card():
            section_title('Jurnal Manual / Penyesuaian', 'Untuk penyusutan, koreksi, atau transaksi di luar menu')
            self.editor = ui.refreshable(self._editor)
            self.editor()

    def _set_line(self, line: dict, key: str, value) -> None:
        line[key] = value
        self.status.refresh()

    def _editor(self) -> None:
        with ui.row().classes('w-full no-wrap gap-3'):
            ui.date_input('Tanggal', value=self.state['date'],
                          on_change=lambda e: self.state.update(date=e.value)).props(
                f'{INPUT_PROPS} data-testid=mj-date-input').classes('w-48')
            ui.input('Keterangan', value=self.state['description'],
                     on_change=lambda e: self.state.update(description=e.value)).props(
                f'{INPUT_PROPS} data-testid=mj-description-input').classes('w-full')
        for i, line in enumerate(self.lines):
            with ui.row().classes('w-full no-wrap gap-2 items-center'):
                ui.select(self.options, label='Akun', value=line['account_id'], with_input=True,
                          on_change=lambda e, ln=line: self._set_line(ln, 'account_id', e.value)).props(
                    f'{INPUT_PROPS} data-testid=mj-line-{i}-account').classes('w-full')
                ui.number('Debit', value=line['debit'], min=0, format='%.0f',
                          on_change=lambda e, ln=line: self._set_line(ln, 'debit', e.value)).props(
                    f'{INPUT_PROPS} data-testid=mj-line-{i}-debit').classes('w-40')
                ui.number('Kredit', value=line['credit'], min=0, format='%.0f',
                          on_change=lambda e, ln=line: self._set_line(ln, 'credit', e.value)).props(
                    f'{INPUT_PROPS} data-testid=mj-line-{i}-credit').classes('w-40')
                icon_button('close', 'Hapus baris', lambda ln=line: self._remove(ln), f'mj-line-{i}-remove')
        with ui.row().classes('w-full items-center justify-between'):
            ui.button('Tambah Baris', icon='add', on_click=self._add).props(
                'flat color=primary no-caps data-testid=mj-add-line-button')
            self.status = ui.refreshable(self._status)
            self.status()
        ui.button('Simpan Jurnal', icon='check', on_click=self.save).props(
            'unelevated color=primary data-testid=mj-submit-button')

    def _status(self) -> None:
        debit, credit = self.totals()
        balanced = debit == credit and debit > 0
        with ui.row().classes('items-center gap-4 no-wrap'):
            ui.label(f'Debit {rp(debit)}').classes('font-mono text-sm text-primary')
            ui.label(f'Kredit {rp(credit)}').classes('font-mono text-sm text-secondary')
            badge('SEIMBANG' if balanced else f'SELISIH {rp(abs(debit - credit))}', 'moss' if balanced else 'rose') \
                .props('data-testid=mj-balance-status')

    def _add(self) -> None:
        self.lines.append({'account_id': None, 'debit': None, 'credit': None})
        self.editor.refresh()

    def _remove(self, line: dict) -> None:
        if len(self.lines) > 2:
            self.lines.remove(line)
            self.editor.refresh()

    def save(self) -> None:
        lines = [(ln['account_id'], float(ln['debit'] or 0), float(ln['credit'] or 0)) for ln in self.lines]
        if run_safely(lambda: journal.create_manual_entry(self.state['date'], self.state['description'], lines,
                                                          self.user['id']), 'Jurnal manual tersimpan.'):
            self.reset()
            self.editor.refresh()
            self.on_saved()


def manual_list(user: dict, period: Period, refresh_all) -> None:
    data = reports.general_journal(period.start, period.end)
    manual = [e for e in data['entries'] if e['source'] == 'MANUAL']
    allow_delete = can(user['role'], 'delete')

    def ask(entry):
        confirm(f'Hapus jurnal {entry["ref_no"]}?',
                lambda: run_safely(lambda: journal.delete_manual_entry(entry['id']), 'Jurnal dihapus.', refresh_all))

    rows = [[tgl(e['date']), e['ref_no'], e['description'], rp(sum(ln['debit'] for ln in e['lines'])),
             (lambda e=e: icon_button('delete_outline', 'Hapus', lambda: ask(e), f'mj-delete-{e["id"]}', 'negative'))
             if allow_delete else ''] for e in manual]
    with card():
        section_title('Riwayat Jurnal Manual', period.label)
        data_table([('Tanggal', 'left'), ('No. Ref', 'left'), ('Keterangan', 'left'), ('Nilai', 'right'),
                    ('', 'right')], rows, 'Belum ada jurnal manual pada periode ini.', 'mj-table')


@protected('/jurnal', 'Jurnal & Buku Besar')
def journal_page(user: dict) -> None:
    ledger_state: dict = {}
    allow_manual = can(user['role'], 'journal.manual')
    actions = page_header('Jurnal & Buku Besar', 'Semua jurnal tercatat otomatis dari transaksi')

    def refresh_all():
        for panel in panels:
            panel.refresh()

    period = Period(refresh_all, 'journal-period')
    with actions:
        period.render()
    with ui.tabs().props('dense align=left no-caps active-color=primary indicator-color=primary') \
            .classes('text-muted') as tabs:
        t_ju = ui.tab('Jurnal Umum').props('data-testid=tab-general-journal')
        t_bb = ui.tab('Buku Besar').props('data-testid=tab-ledger')
        t_ns = ui.tab('Neraca Saldo').props('data-testid=tab-trial-balance')
        t_jm = ui.tab('Jurnal Manual').props('data-testid=tab-manual-journal') if allow_manual else None
    panels = [ui.refreshable(lambda: general_journal_tab(period)),
              ui.refreshable(lambda: ledger_tab(period, ledger_state)),
              ui.refreshable(lambda: trial_balance_tab(period))]
    if allow_manual:
        panels.append(ui.refreshable(lambda: manual_list(user, period, refresh_all)))
    with ui.tab_panels(tabs, value=t_ju).classes('w-full bg-transparent'):
        for tab, panel in zip([t_ju, t_bb, t_ns], panels):
            with ui.tab_panel(tab).classes('p-0'), card():
                panel()
        if allow_manual:
            with ui.tab_panel(t_jm).classes('p-0 gap-4'):
                ManualJournal(user, refresh_all).render()
                panels[3]()
