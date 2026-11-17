from nicegui import ui

from services import reports
from views.components import badge, card, page_header, report_block
from views.fmt import kg, rp
from views.layout import protected
from views.period import Period


def income_tab(period: Period) -> None:
    data = reports.income_statement(period.start, period.end)
    rows = [(['PENDAPATAN', ''], 'section')]
    rows += [([f'{INDENT}{r["code"]} {r["name"]}', rp(r['amount'])], '') for r in data['revenues']]
    rows += [(['Total Pendapatan', rp(data['total_revenue'])], 'bold'), (['BEBAN', ''], 'section')]
    rows += [([f'{INDENT}{r["code"]} {r["name"]}', rp(r['amount'])], '') for r in data['expenses']]
    rows += [(['Total Beban', rp(data['total_expense'])], 'bold'),
             (['LABA (RUGI) BERSIH', rp(data['net_income'])], 'bold')]
    report_block(title='Laporan Laba Rugi', subtitle=period.label, headers=[('Keterangan', 'left'), ('Jumlah', 'right')],
                 rows=rows, widths=[70, 30], filename='laporan-laba-rugi.pdf', testid='income-statement')


def balance_tab(period: Period) -> None:
    data = reports.balance_sheet(period.end)
    section = lambda items: [([f'{INDENT}{r["code"]} {r["name"]}'.rstrip(), rp(r['amount'])], '')  # noqa: E731
                             for r in items]
    rows = [(['ASET', ''], 'section'), *section(data['assets']), (['TOTAL ASET', rp(data['total_assets'])], 'bold'),
            (['KEWAJIBAN', ''], 'section'), *section(data['liabilities']),
            (['Total Kewajiban', rp(data['total_liabilities'])], 'bold'),
            (['MODAL', ''], 'section'), *section(data['equity']),
            (['Total Modal', rp(data['total_equity'])], 'bold'),
            (['TOTAL KEWAJIBAN + MODAL', rp(data['total_liabilities'] + data['total_equity'])], 'bold')]
    badge('NERACA SEIMBANG' if data['balanced'] else 'NERACA TIDAK SEIMBANG — periksa saldo awal Bagan Akun',
          'moss' if data['balanced'] else 'rose').props('data-testid=balance-sheet-status')
    report_block(title='Neraca', subtitle=period.end_label, headers=[('Keterangan', 'left'), ('Jumlah', 'right')],
                 rows=rows, widths=[70, 30], filename='neraca.pdf', testid='balance-sheet')


def cash_flow_tab(period: Period) -> None:
    data = reports.cash_flow(period.start, period.end)
    rows = [(['Saldo Kas & Bank Awal', rp(data['opening'])], 'bold')]
    for sec in data['sections']:
        rows.append(([sec['title'], ''], 'section'))
        rows += [([f'{INDENT}{r["label"]}', rp(r['amount'])], '') for r in sec['rows']] or [
            ([f'{INDENT}Tidak ada arus kas', rp(0)], 'muted')]
        rows.append(([f'Kas Bersih {sec["title"].replace("Arus Kas dari ", "")}', rp(sec['total'])], 'bold'))
    rows += [(['Kenaikan (Penurunan) Kas Bersih', rp(data['net'])], 'bold'),
             (['Saldo Kas & Bank Akhir', rp(data['closing'])], 'bold')]
    report_block(title='Laporan Arus Kas', subtitle=f'{period.label} · metode langsung',
                 headers=[('Keterangan', 'left'), ('Jumlah', 'right')], rows=rows, widths=[70, 30],
                 filename='laporan-arus-kas.pdf', testid='cash-flow')


def stock_tab(period: Period) -> None:
    data = reports.stock_report(period.start, period.end)
    rows = [([r['name'], kg(r['opening']), kg(r['in']), kg(r['out']), kg(r['closing']), rp(r['price']),
              rp(r['value'])], '') for r in data['rows']]
    rows.append((['TOTAL', '', '', '', kg(data['total_kg']), '', rp(data['total_value'])], 'bold'))
    report_block(title='Laporan Stok Kepiting', subtitle=period.label,
                 headers=[('Produk', 'left'), ('Stok Awal', 'right'), ('Masuk', 'right'), ('Keluar', 'right'),
                          ('Stok Akhir', 'right'), ('Harga/kg', 'right'), ('Nilai', 'right')],
                 rows=rows, widths=[26, 12, 12, 12, 12, 12, 14], filename='laporan-stok.pdf', testid='stock-report',
                 orientation='L')


INDENT = '\u2003\u2003'
TABS = [('Laba Rugi', 'income', income_tab), ('Neraca', 'balance', balance_tab),
        ('Arus Kas', 'cashflow', cash_flow_tab), ('Stok', 'stock', stock_tab)]


@protected('/laporan', 'Laporan Keuangan')
def reports_page(user: dict) -> None:
    actions = page_header('Laporan Keuangan', 'Laba rugi, neraca, arus kas, dan stok — siap cetak PDF')
    panels: list = []
    period = Period(lambda: [p.refresh() for p in panels], 'report-period')
    with actions:
        period.render()
    with ui.tabs().props('dense align=left no-caps active-color=primary indicator-color=primary') \
            .classes('text-muted') as tabs:
        tabs_list = [ui.tab(label).props(f'data-testid=tab-{slug}') for label, slug, _ in TABS]
    with ui.tab_panels(tabs, value=tabs_list[0]).classes('w-full bg-transparent'):
        for tab, (_, _, builder) in zip(tabs_list, TABS):
            with ui.tab_panel(tab).classes('p-0'), card():
                panel = ui.refreshable(lambda b=builder: b(period))
                panels.append(panel)
                panel()
