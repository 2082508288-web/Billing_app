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
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QIcon

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


def run_embedded_server():
    """
    Entry point used when this program is launched as
    `ClothShopBilling.exe --run-server`.

    Bug fix: the Application Status tab's "Start Server" button has
    always launched the server this way once the app is packaged as a
    .exe -- there's normally no separate Python interpreter on the shop
    PC to run clothshop_billing_server/run_server.py directly, so
    status_tab.py re-launches the exe itself with this flag instead.
    The problem was that main.py never actually checked for the flag,
    so "Start Server" just opened a second full GUI window instead of a
    server -- which is exactly what staff were seeing as "errors" when
    turning the server on and off. This makes the flag do what it was
    always meant to: run the FastAPI server in this process.

    It uses the exact same shared database
    (~/.cloth_shop_billing/cloth_shop.db) the desktop app already uses --
    nothing about the schema, the data, or its location changes.
    """
    import importlib.util

    # Bundling layout differs between a source checkout and a frozen
    # .exe: in source, clothshop_billing_server/ sits one level above
    # this file (app/main.py); in a frozen build it's bundled at the
    # root of the PyInstaller bundle (see build_windows.bat's
    # --add-data), so resource_path() finds it directly. Mirrors the
    # same frozen/source branching status_tab.py already does for the
    # QR code image.
    if getattr(sys, "frozen", False):
        server_root = resource_path("clothshop_billing_server")
    else:
        server_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "clothshop_billing_server")
        )

    backend_dir = os.path.join(server_root, "backend")
    main_py_path = os.path.join(backend_dir, "main.py")

    if not os.path.exists(main_py_path):
        print(f"ERROR: server backend not found at {main_py_path}")
        sys.exit(1)

    # backend/main.py does `from database import Database` (a bare,
    # same-folder import), so backend_dir must be on sys.path before we
    # load it -- exactly like running `python main.py` from inside that
    # folder would give it for free.
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Loaded by file path (not `import main`) so this can never collide
    # with this file -- the desktop app's own main.py -- regardless of
    # how Python happens to have named this running script in
    # sys.modules.
    spec = importlib.util.spec_from_file_location(
        "clothshop_server_main", main_py_path
    )
    server_main = importlib.util.module_from_spec(spec)
    sys.modules["clothshop_server_main"] = server_main
    spec.loader.exec_module(server_main)

    import uvicorn

    uvicorn.run(server_main.app, host="0.0.0.0", port=5000, log_level="info")


APP_ICON_PATH = resource_path(os.path.join("assets", "icon.ico"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cloth Shop Billing System")
        self.resize(1300, 820)

        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))

        self.db = Database()

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
        self.tabs.addTab(self.balances_tab, "Balances")
        self.tabs.addTab(self.expenses_tab, "Expenses")
        self.tabs.addTab(self.sales_tab, "Sales History")
        self.tabs.addTab(self.stats_tab, "Statistics")
        self.tabs.addTab(self.status_tab, "Application Status")

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_catalog_changed(self):
        self.billing_tab.refresh_catalog()

    def closeEvent(self, event):
        self.status_tab.shutdown_server()
        event.accept()

    def _on_bill_saved(self):
        self.sales_tab.refresh()
        self.stats_tab.refresh()
        self.customers_tab._refresh_customer_list()
        self.balances_tab.refresh()

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)

        if widget is self.sales_tab:
            self.sales_tab.refresh()
        elif widget is self.stats_tab:
            self.stats_tab.refresh()
        elif widget is self.customers_tab:
            self.customers_tab._refresh_customer_list()
        elif widget is self.balances_tab:
            self.balances_tab.refresh()
        elif widget is self.expenses_tab:
            self.expenses_tab.refresh()


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
    # Must be checked before QApplication is created -- when frozen and
    # re-launched with this flag (see status_tab.py / run_embedded_server
    # above), this process should run headless as the FastAPI server,
    # never open a GUI window at all.
    if "--run-server" in sys.argv:
        run_embedded_server()
    else:
        main()
