"""
main.py
-------
Entry point for the Cloth Shop Billing System.
"""

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QTableWidget,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QDate

from database import Database
from theme import STYLESHEET
from billing_tab import BillingTab
from inventory_tab import InventoryTab
from customers_tab import CustomersTab
from sales_tab import SalesTab
from status_tab import StatusTab
from stats_tab import StatsTab
from balances_tab import BalancesTab
from expenses_tab import ExpensesTab


def resource_path(relative_path):
    """Resolve a bundled resource path for source runs and PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


APP_ICON_PATH = resource_path(os.path.join("assets", "icon.ico"))


class MainWindow(QMainWindow):
    def __init__(self, db=None):
        super().__init__()
        self.setWindowTitle("Cloth Shop Billing System")
        self.resize(1300, 820)

        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))

        self.db = db or Database()

        central = QWidget()
        central.setObjectName("centralWidget")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.status_tab = StatusTab(self.db)
        self.customers_tab = CustomersTab(self.db)
        self.balances_tab = BalancesTab(self.db)
        self.expenses_tab = ExpensesTab(self.db)
        self.sales_tab = SalesTab(self.db)
        self.stats_tab = StatsTab(self.db)
        self.inventory_tab = InventoryTab(
            self.db, on_catalog_changed=self._on_catalog_changed
        )
        self.billing_tab = BillingTab(
            self.db, on_bill_saved=self._on_bill_saved
        )

        self.tabs.addTab(self.billing_tab, "New Bill")
        self.tabs.addTab(self.inventory_tab, "Inventory")
        self.tabs.addTab(self.customers_tab, "Customers")
        self.tabs.addTab(self.balances_tab, "Payments && Balances")
        self.tabs.addTab(self.expenses_tab, "Expenses")
        self.tabs.addTab(self.sales_tab, "Sales History")
        self.tabs.addTab(self.stats_tab, "Statistics")
        self.tabs.addTab(self.status_tab, "Data && Backups")

        for table in self.findChildren(QTableWidget):
            table.verticalHeader().hide()
            table.verticalHeader().setDefaultSectionSize(38)
            table.setAlternatingRowColors(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self._refresh_reports)
        self.db.on_change = lambda: self.refresh_timer.start(0)

    def _on_catalog_changed(self):
        self.billing_tab.refresh_catalog()

    def closeEvent(self, event):
        self.db.on_change = None
        self.refresh_timer.stop()
        event.accept()

    def _on_bill_saved(self, bill_id):
        bill, _ = self.db.get_bill(bill_id)
        self.sales_tab.show_saved_bill(bill["bill_date"])
        start, end = self.stats_tab._date_range()
        if not start <= bill["bill_date"][:10] <= end:
            self.stats_tab.quick_range_combo.setCurrentText("All time")
        self.balances_tab.selected_customer_id = "all"
        self._refresh_reports()

    def _refresh_reports(self):
        self.refresh_timer.stop()
        self.sales_tab.refresh()
        self.stats_tab.refresh()
        self.customers_tab.refresh()
        self.balances_tab.refresh()
        self.expenses_tab.refresh()
        self.inventory_tab._refresh_items()

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
        elif widget is self.inventory_tab:
            widget._refresh_categories()
        elif widget is self.billing_tab:
            widget.bill_date_input.setMaximumDate(QDate.currentDate())
            widget.refresh_catalog()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("Cloth Shop Billing System")

    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
