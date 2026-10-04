"""Regressions for local billing, ledgers, receipts, and daily reporting.

Run: QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QDate, QUrl
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from database import Database, SCHEMA
from main import MainWindow
from receipt import ReceiptDialog, _make_payment_qr_image, _upi_payment_uri, _balance_amount

APP = QApplication.instance() or QApplication([])


class BillingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'shop.db')
        self.db = Database(self.path)
        self.today = date.today().isoformat()
        self.window = None

    def tearDown(self):
        if self.window:
            self.window.close()
        APP.processEvents()
        self.temp.cleanup()

    def sale(self, amount=105, paid=0, customer=None, day=None):
        return self.db.save_bill(customer,
            [{'name': 'Test shirt', 'quantity': 1, 'rate': 100, 'subtotal': 100,
              'gst_rate': 5, 'gst_amount': 5}],
            100, 0, 0, amount, 'Cash', bill_date=day or self.today,
            taxable_amount=100, gst_rate=5, gst_amount=5, initial_payment_amount=paid)[0]

    def open_window(self):
        self.window = MainWindow(self.db)
        return self.window

    def test_unpaid_and_partial_bills_survive_restart(self):
        credit = self.sale()
        partial = self.sale(paid=25)
        for _ in range(2):
            self.db = Database(self.path)
            self.assertEqual(self.db.get_bill_paid_amount(credit), 0)
            self.assertEqual(self.db.get_bill_balance(credit), 105)
            self.assertEqual(self.db.get_bill_balance(partial), 80)

    def test_legacy_bills_migrate_once(self):
        legacy_path = str(Path(self.temp.name) / 'legacy.db')
        with sqlite3.connect(legacy_path) as conn:
            conn.executescript(SCHEMA)
            conn.execute("INSERT INTO bills(bill_no,subtotal,total) VALUES ('OLD',100,100)")
        legacy = Database(legacy_path)
        self.assertEqual(legacy.get_bill_paid_amount(1), 100)
        self.assertEqual(len(Database(legacy_path).get_bill_payment_history(1)), 1)

    def test_receipt_reports_actual_payments(self):
        bill_id = self.sale(paid=25)
        self.db.add_payment(bill_id, 30)
        bill, _ = self.db.get_bill(bill_id)
        self.assertEqual(bill['paid_amount'], 55)
        self.assertEqual(_balance_amount(bill), 50)
        self.assertEqual(self.db.stat_totals()['payments_collected'], 55)

    def test_atomic_failure_does_not_publish_or_save_bill(self):
        notices = []
        self.db.on_change = lambda: notices.append(True)
        with self.assertRaises(ValueError):
            self.db.save_bill(None, [{'name':'Bad', 'quantity':0}], 10, 0, 0, 10, 'Cash')
        self.assertEqual(self.db.search_bills(), [])
        self.assertEqual(notices, [])

    def test_overpayment_is_rejected(self):
        bill_id = self.sale(paid=25)
        with self.assertRaises(ValueError):
            self.db.add_payment(bill_id, 81)
        self.assertEqual(self.db.get_bill_paid_amount(bill_id), 25)

    def test_zero_sales_days_and_boundaries(self):
        self.sale(day='2026-01-02')
        self.sale(day='2026-01-04')
        daily = self.db.stat_daily_sales('2026-01-01', '2026-01-05')
        self.assertEqual([r['revenue'] for r in daily], [0,105,0,105,0])
        self.assertEqual(daily[-1]['d'], '2026-01-05')
        self.assertEqual(self.db.stat_daily_sales('2026-02-02', '2026-02-01'), [])

    def test_expenses_with_existing_rows_upgrade(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute('ALTER TABLE expenses RENAME TO old_expenses')
            conn.execute('CREATE TABLE expenses (id INTEGER PRIMARY KEY, expense_date TEXT, category TEXT, amount REAL, payment_mode TEXT, description TEXT)')
            conn.execute("INSERT INTO expenses VALUES (1,'2026-01-01','Rent',100,'Cash','')")
            conn.execute('DROP TABLE old_expenses')
        self.db = Database(self.path)
        self.db.add_expense('Rent', 25)
        self.assertEqual(len(self.db.get_expenses()), 2)
        self.open_window().expenses_tab.refresh()

    def test_payment_view_includes_walk_ins_and_customers(self):
        customer = self.db.add_customer('Test Customer', '5550001')
        self.sale(paid=50)
        self.sale(customer=customer, paid=105)
        tab = self.open_window().balances_tab
        self.assertEqual(tab.bill_table.rowCount(), 2)
        self.assertEqual(tab.payment_table.rowCount(), 2)
        self.assertIn('155.00', tab.total_paid_label.text())
        tab.selected_customer_id = None
        tab.refresh()
        self.assertEqual(tab.bill_table.rowCount(), 1)
        self.assertEqual(tab.payment_table.rowCount(), 1)
        self.assertEqual(tab.customer_heading.text(), 'Walk-in sales')

    def test_save_updates_reports_before_receipt_and_clears_cart(self):
        window = self.open_window()
        tab = window.billing_tab
        tab.cart = [{'item_id': None, 'name': 'Test shirt', 'category': 'Shirts',
                     'qty': 1, 'rate': 100, 'amount': 100, 'discount': 0, 'gst_rate': 5}]
        tab._render_cart()
        tab._recalculate_totals()
        tab.payment_amount_input.setValue(25)
        tab.bill_date_input.setDate(QDate.currentDate().addDays(-60))
        window.sales_tab.quick_range_combo.setCurrentText('Today')
        window.sales_tab.search_input.setText('unrelated search')
        def receipt_open(dialog):
            self.assertEqual(tab.cart, [])
            self.assertEqual(window.sales_tab.bills_table.rowCount(), 1)
            self.assertEqual(window.balances_tab.bill_table.rowCount(), 1)
            self.assertEqual(window.balances_tab.payment_table.rowCount(), 1)
            return QDialog.Accepted
        with patch.object(ReceiptDialog, 'exec', receipt_open):
            tab._complete_bill()
        self.assertEqual(window.stats_tab.quick_range_combo.currentText(), 'All time')
        self.assertEqual(tab.bill_date_input.date(), QDate.currentDate())
        self.assertEqual(self.db.get_bill_balance(1), 80)

    def test_receipt_failure_does_not_leave_cart_for_duplicate_sale(self):
        window = self.open_window()
        tab = window.billing_tab
        tab.cart = [{'item_id': None, 'name':'Test', 'category':'Shirts', 'qty':1,
                     'rate':100, 'amount':100, 'discount':0, 'gst_rate':5}]
        tab._render_cart()
        tab._recalculate_totals()
        with patch('billing_tab.ReceiptDialog', side_effect=RuntimeError('Printer unavailable')), patch('billing_tab.QMessageBox.warning') as warning:
            tab._complete_bill()
        self.assertEqual(len(self.db.search_bills()), 1)
        self.assertEqual(tab.cart, [])
        self.assertIn('was saved', warning.call_args.args[2])

    def test_write_notifications_refresh_payment_and_delete_views(self):
        bill_id = self.sale(paid=25)
        window = self.open_window()
        self.db.add_payment(bill_id, 80)
        APP.processEvents()
        self.assertEqual(window.balances_tab.payment_table.rowCount(), 2)
        self.assertIn('0.00', window.balances_tab.total_outstanding_label.text())
        self.db.delete_bill(bill_id)
        APP.processEvents()
        self.assertEqual(window.sales_tab.bills_table.rowCount(), 0)
        self.assertEqual(window.balances_tab.bill_table.rowCount(), 0)
        self.assertEqual(window.balances_tab.payment_table.rowCount(), 0)

    def test_chart_has_seven_days_including_zero_days(self):
        self.sale()
        stats = self.open_window().stats_tab
        bars = stats.trend_figure.axes[0].patches
        self.assertEqual(len(bars), 7)
        self.assertEqual([bar.get_height() for bar in bars], [0,0,0,0,0,0,105])
        self.assertEqual(len(stats.trend_figure.axes[0].get_xticklabels()), 7)

    def test_free_bill_chart_does_not_crash(self):
        self.db.save_bill(None, [{'name':'Gift','quantity':1,'rate':0,'subtotal':0}], 0,0,0,0,'Cash')
        self.open_window().stats_tab.refresh()

    def test_manual_sales_filter_and_invalid_range(self):
        tab = self.open_window().sales_tab
        tab.date_from.setDate(QDate.currentDate().addDays(-10))
        self.assertEqual(tab.quick_range_combo.currentText(), 'Custom')
        tab.date_to.setDate(QDate.currentDate().addDays(-11))
        tab.refresh()
        self.assertEqual(tab._bills_cache, [])
        self.assertIn('start date', tab.summary_label.text())

    def test_qr_resource_and_pdf(self):
        bill, items = self.db.get_bill(self.sale(paid=25))
        uri = _upi_payment_uri(bill, _balance_amount(bill))
        self.assertEqual(parse_qs(urlparse(uri).query)['am'], ['80.00'])
        image = _make_payment_qr_image(bill, 80)
        self.assertFalse(image.isNull())
        dialog = ReceiptDialog(bill, items)
        resource = dialog.text_edit.document().resource(QTextDocument.ImageResource, QUrl('qr://invoice-payment'))
        self.assertFalse(resource.isNull())
        printer = QPrinter(QPrinter.HighResolution)
        dialog._configure_printer(printer)
        printer.setOutputFormat(QPrinter.PdfFormat)
        output = Path(self.temp.name) / 'receipt.pdf'
        printer.setOutputFileName(str(output))
        dialog._prepare_document_for_printer(printer)
        dialog.text_edit.document().print_(printer)
        self.assertTrue(output.read_bytes().startswith(b'%PDF'))
        self.assertGreater(output.stat().st_size, 1000)
        dialog.close()

    def test_backup_and_export_preserve_records(self):
        self.sale(paid=25)
        backup = self.db.backup_database(str(Path(self.temp.name)/'backups'))
        with sqlite3.connect(backup) as conn:
            self.assertEqual(conn.execute('SELECT SUM(amount) FROM payments').fetchone()[0], 25)
        files = self.db.export_all_tables_csv(str(Path(self.temp.name)/'csv'))
        self.assertIn('payments.csv', [Path(f).name for f in files])


if __name__ == '__main__':
    unittest.main()
