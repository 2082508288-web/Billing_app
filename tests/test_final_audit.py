"""Boundary regressions found in the final billing/data reliability scan."""
import csv
from contextlib import closing
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/os.environ.get('BILLING_APP_DIR','app')))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QMessageBox
from database import Database
from access import AccessSession,RoleDatabase
from billing_tab import BillingTab
from balances_tab import ReceivePaymentDialog
from money import sum_money


class FinalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)
        self.db=Database(str(self.path/'audit.db'))
        self.session=AccessSession();self.session.login('1852j')
        self.access=RoleDatabase(self.db,self.session)
        self.cid=self.db.add_customer('Example','123')
        self.category=self.db.get_categories()[0]['id']
        self.errors=[];hook=sys.excepthook
        sys.excepthook=lambda *args:self.errors.append(args[1])
        self.addCleanup(setattr,sys,'excepthook',hook)
        for name in ('warning','critical','information'):
            mock=patch.object(QMessageBox,name);mock.start();self.addCleanup(mock.stop)

    def tearDown(self):
        self.app.processEvents()
        self.assertEqual(self.errors,[])

    def bill(self,total=1):
        return self.db.save_bill(self.cid,[dict(name='Fixture',quantity=1,rate=total,subtotal=total)],
            total,0,0,total,'Cash',initial_payment_amount=0)[0]

    def tab(self):
        tab=BillingTab(self.access);self.addCleanup(tab.close);return tab

    def test_fractional_historical_payments_match_reports_receipts_and_collection(self):
        bid=self.bill()
        with self.db._conn() as conn:
            conn.executemany("INSERT INTO payments(bill_id,customer_id,amount) VALUES (?,?,?)",[(bid,self.cid,v) for v in (.1,.7,.005)])
        self.assertEqual(self.db.report_bills()[0]['paid'],.81)
        self.assertEqual(self.db.get_bill_paid_amount(bid),.81)
        self.assertEqual(self.db.get_bill_balance(bid),.19)
        bill,items=self.db.get_bill(bid)
        self.assertEqual((bill['paid_amount'],bill['balance']),(.81,.19))
        dialog=ReceivePaymentDialog(self.access,bill);self.addCleanup(dialog.close)
        self.assertEqual(dialog.amount_input.maximum(),.19)
        with self.assertRaises(ValueError):self.db.add_payment(bid,.20)
        self.db.add_payment(bid,.19)
        self.assertEqual(self.db.get_bill_balance(bid),0)
        self.assertEqual(self.db.report_bills()[0]['balance'],0)

    def test_customer_balance_rounds_each_bill_not_each_payment(self):
        first=self.bill();second=self.bill()
        with self.db._conn() as conn:
            conn.executemany('INSERT INTO payments(bill_id,customer_id,amount) VALUES (?,?,?)',
                             [(first,self.cid,.005),(first,self.cid,.005),(second,self.cid,2)])
        expected=dict(total_billed=2,total_paid=2.01,balance=.99)
        self.assertEqual(self.db.get_customer_balance(self.cid),expected)
        row=self.db.get_customer_balances()[0]
        self.assertEqual({key:row[key] for key in expected},expected)
        self.assertEqual(sum_money(b['balance'] for b in self.db.report_bills()),.99)

    def test_cart_invalid_quantities_and_prices_never_change_saved_draft(self):
        iid=self.db.add_item('Item',self.category,None,'','','',100,20)
        tab=self.tab();tab._add_to_cart(iid,'Item','Category',2,100,5)
        original=dict(tab.cart[0])
        for text in ('inf','1e309','NaN','1.5','0','-2','999999999999999999999999999999999999'):
            with self.subTest(quantity=text):
                tab.cart_table.item(0,2).setText(text)
                self.assertEqual(tab.cart[0],original)
                self.assertEqual(tab._grand_total(),210)
                self.assertEqual(self.errors,[])
        for text in ('1e50','NaN','inf'):
            with self.subTest(rate=text):
                tab.cart_table.item(0,3).setText(text)
                self.assertEqual(tab.cart[0],original)
                self.assertEqual(self.errors,[])

    def test_zero_cent_savings_lines_still_share_bundle_gst(self):
        ids=[self.db.add_item(f'Bundle item {i}',self.category,None,'','','',rate,10) for i,rate in enumerate((100.10,100.10,800))]
        oid=self.db.save_offer('Small saving',3,1000.19,[(self.category,0)])
        self.session.logout()
        tab=self.tab()
        for iid,rate in zip(ids,(100.10,100.10,800)):
            tab._add_to_cart(iid,'Bundle item','Category',1,rate,5)
        self.assertEqual(sum_money(r['offer_discount'] for r in tab.cart),.01)
        self.assertEqual([r['offer_id'] for r in tab.cart],[oid]*3)
        self.assertEqual(tab._gst_amount(),50.01)
        self.assertEqual(tab._grand_total(),1050.20)
        with patch('billing_tab.ReceiptDialog'):tab._complete_bill()
        saved=self.db.search_bills()[0]
        self.assertEqual(saved['total'],1050.20)
        self.assertEqual(self.db.report_statistics()['totals']['revenue'],1050.20)

    def test_repeated_backup_never_overwrites_previous_copy(self):
        if not hasattr(self.db,'backup_database'):self.skipTest('Backup exists in recommended copy only')
        with patch('database.datetime') as clock:
            clock.now.return_value=datetime(2026,10,5,12,0,0)
            first=self.db.backup_database(str(self.path/'backups'))
            self.db.add_customer('Later','456')
            second=self.db.backup_database(str(self.path/'backups'))
        self.assertNotEqual(first,second)
        with closing(sqlite3.connect(first)) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0],1)
        with closing(sqlite3.connect(second)) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0],2)

    def test_whole_database_csv_has_one_snapshot_during_writes(self):
        if not hasattr(self.db,'export_all_tables_csv'):self.skipTest('Whole database export exists in recommended copy only')
        self.bill()
        original=csv.writer
        mutated=[]
        db=self.db
        class Writer:
            def __init__(self,stream,*args,**kwargs):
                self.stream=stream;self.writer=original(stream,*args,**kwargs)
            def writerow(self,row):
                self.writer.writerow(row)
                if Path(self.stream.name).name=='bills.csv' and row and row[0]!='id' and not mutated:
                    mutated.append(True)
                    db.save_bill(self_cid,[dict(name='During export',quantity=1,rate=2,subtotal=2)],2,0,0,2,'Cash')
        self_cid=self.cid
        with patch('database.csv.writer',Writer):self.db.export_all_tables_csv(str(self.path/'export'))
        with (self.path/'export/bills.csv').open() as f:bills=list(csv.DictReader(f))
        with (self.path/'export/payments.csv').open() as f:payments=list(csv.DictReader(f))
        self.assertEqual(mutated,[True])
        self.assertEqual(len(self.db.search_bills()),2)
        self.assertEqual(len(bills),1)
        self.assertEqual(payments,[])


if __name__=='__main__':unittest.main()
