"""
sales_tab.py
------------
A record of everything sold: filter by date range or search, view any
bill's line items, reprint, or export to CSV.
"""

import csv
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QComboBox, QSpinBox, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QDate

from widgets import rupees, make_heading, confirm_delete_password
from receipt import ReceiptDialog


class SalesTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._bills_cache = []
        self._build_ui()
        self.date_from.dateChanged.connect(self._use_custom_range)
        self.date_to.dateChanged.connect(self._use_custom_range)
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        outer.addWidget(make_heading("Sales History", "Every bill, what sold, and when"))

        filter_box = QGroupBox("Filters")
        filter_layout = QVBoxLayout(filter_box)
        filter_row = QHBoxLayout()
        filter_layout.addLayout(filter_row)

        filter_row.addWidget(QLabel("From:"))
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        self._set_date(self.date_from, QDate.currentDate().addMonths(-1))
        filter_row.addWidget(self.date_from)

        filter_row.addWidget(QLabel("To:"))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        self._set_date(self.date_to, QDate.currentDate())
        filter_row.addWidget(self.date_to)

        self.quick_range_combo = QComboBox()
        self.quick_range_combo.addItems(["Custom", "Today", "Last 7 days", "Last 30 days", "This month", "All time"])
        self.quick_range_combo.currentTextChanged.connect(self._apply_quick_range)
        filter_row.addWidget(self.quick_range_combo)

        filter_row.addStretch()
        filter_row = QHBoxLayout()
        filter_layout.addLayout(filter_row)

        # Month-range picker: lets the user pick "from this month ...
        # to this month" directly (e.g. Jan 2026 to Jun 2026) instead of
        # having to pick exact days, and feeds the same date_from/date_to
        # used everywhere below -- including "Export CSV", so exporting
        # a specific range of months is just: pick the two months here,
        # click Apply, then Export CSV.
        filter_row.addWidget(QLabel("  Month range:"))
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        today = QDate.currentDate()

        self.from_month_combo = QComboBox()
        self.from_month_combo.addItems(month_names)
        self.from_month_combo.setCurrentIndex(today.month() - 1)
        filter_row.addWidget(self.from_month_combo)

        self.from_year_spin = QSpinBox()
        self.from_year_spin.setRange(2000, today.year() + 1)
        self.from_year_spin.setValue(today.year())
        filter_row.addWidget(self.from_year_spin)

        filter_row.addWidget(QLabel("to"))

        self.to_month_combo = QComboBox()
        self.to_month_combo.addItems(month_names)
        self.to_month_combo.setCurrentIndex(today.month() - 1)
        filter_row.addWidget(self.to_month_combo)

        self.to_year_spin = QSpinBox()
        self.to_year_spin.setRange(2000, today.year() + 1)
        self.to_year_spin.setValue(today.year())
        filter_row.addWidget(self.to_year_spin)

        apply_month_range_btn = QPushButton("Apply")
        apply_month_range_btn.setProperty("role", "secondary")
        apply_month_range_btn.setToolTip("Set the date filters above to this month range")
        apply_month_range_btn.clicked.connect(self._apply_month_range)
        filter_row.addWidget(apply_month_range_btn)

        filter_row.addStretch()
        filter_row = QHBoxLayout()
        filter_layout.addLayout(filter_row)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search bill no / customer / phone...")
        filter_row.addWidget(self.search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.refresh)
        filter_row.addWidget(search_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.setProperty("role", "secondary")
        export_btn.clicked.connect(self._export_csv)
        filter_row.addWidget(export_btn)

        self.search_input.returnPressed.connect(self.refresh)
        self.quick_range_combo.blockSignals(True)
        self.quick_range_combo.setCurrentText("All time")
        self.quick_range_combo.blockSignals(False)
        self._set_date(self.date_from, QDate(2000, 1, 1))
        outer.addWidget(filter_box)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: 600; color: #2f6f4f;")
        outer.addWidget(self.summary_label)

        self.bills_table = QTableWidget(0, 8)
        self.bills_table.verticalHeader().setDefaultSectionSize(40)
        self.bills_table.setHorizontalHeaderLabels(
            ["Bill No", "Date", "Customer", "Pieces", "Subtotal", "Discount", "Total", ""]
        )
        for column in (0, 1, 3, 4, 5, 6):
            self.bills_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.bills_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.bills_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.bills_table.setColumnWidth(7, 90)
        self.bills_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bills_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bills_table.doubleClicked.connect(self._view_bill)
        outer.addWidget(self.bills_table, 1)

        hint = QLabel("Double-click a bill to view / reprint it.")
        hint.setStyleSheet("color: #6c757d; font-size: 11px;")
        outer.addWidget(hint)

    @staticmethod
    def _set_date(widget, value):
        widget.blockSignals(True)
        widget.setDate(value)
        widget.blockSignals(False)

    def _use_custom_range(self):
        self.quick_range_combo.blockSignals(True)
        self.quick_range_combo.setCurrentText("Custom")
        self.quick_range_combo.blockSignals(False)

    def _apply_month_range(self):
        from_year = self.from_year_spin.value()
        from_month = self.from_month_combo.currentIndex() + 1
        to_year = self.to_year_spin.value()
        to_month = self.to_month_combo.currentIndex() + 1

        start = QDate(from_year, from_month, 1)
        end = QDate(to_year, to_month, 1).addMonths(1).addDays(-1)  # last day of that month

        if start > end:
            QMessageBox.warning(
                self, "Invalid range", "The 'from' month must not be after the 'to' month."
            )
            return

        self.quick_range_combo.blockSignals(True)
        self.quick_range_combo.setCurrentText("Custom")
        self.quick_range_combo.blockSignals(False)
        self._set_date(self.date_from, start)
        self._set_date(self.date_to, end)
        self.refresh()

    def _apply_quick_range(self, label):
        today = QDate.currentDate()
        if label == "Today":
            self._set_date(self.date_from, today)
            self._set_date(self.date_to, today)
        elif label == "Last 7 days":
            self._set_date(self.date_from, today.addDays(-6))
            self._set_date(self.date_to, today)
        elif label == "Last 30 days":
            self._set_date(self.date_from, today.addDays(-29))
            self._set_date(self.date_to, today)
        elif label == "This month":
            self._set_date(self.date_from, QDate(today.year(), today.month(), 1))
            self._set_date(self.date_to, today)
        elif label == "All time":
            self._set_date(self.date_from, QDate(2000, 1, 1))
            self._set_date(self.date_to, today)
        else:
            return
        self.refresh()

    def show_saved_bill(self, bill_date):
        """Ensure the just-saved bill is visible, including backdated sales."""
        saved_date = QDate.fromString(bill_date[:10], "yyyy-MM-dd")
        self.search_input.clear()
        self.quick_range_combo.blockSignals(True)
        self.quick_range_combo.setCurrentText("Custom")
        self.quick_range_combo.blockSignals(False)
        self._set_date(self.date_from, min(self.date_from.date(), saved_date))
        self._set_date(self.date_to, max(self.date_to.date(), saved_date))

    def refresh(self):
        # Rolling presets follow the current day even when the app stays open.
        label = self.quick_range_combo.currentText()
        today = QDate.currentDate()
        starts = {"Today": today, "Last 7 days": today.addDays(-6),
                  "Last 30 days": today.addDays(-29),
                  "This month": QDate(today.year(), today.month(), 1),
                  "All time": QDate(2000, 1, 1)}
        if label in starts:
            self._set_date(self.date_from, starts[label])
            self._set_date(self.date_to, today)
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        if date_from > date_to:
            self._bills_cache = []
            self.bills_table.setRowCount(0)
            self.summary_label.setText("Choose a start date on or before the end date.")
            return
        search = self.search_input.text().strip() or None
        bills = self.db.search_bills(date_from=date_from, date_to=date_to, search_text=search)
        self._bills_cache = bills

        self.bills_table.setRowCount(len(bills))
        total_revenue = 0
        total_pieces = 0
        for row_idx, b in enumerate(bills):
            self.bills_table.setItem(row_idx, 0, QTableWidgetItem(b["bill_no"]))
            self.bills_table.setItem(row_idx, 1, QTableWidgetItem(b["bill_date"]))
            self.bills_table.setItem(row_idx, 2, QTableWidgetItem(b["customer_name"] or "Walk-in"))
            self.bills_table.setItem(row_idx, 3, QTableWidgetItem(str(b["piece_count"])))
            self.bills_table.setItem(row_idx, 4, QTableWidgetItem(rupees(b["subtotal"])))
            self.bills_table.setItem(row_idx, 5, QTableWidgetItem(rupees(b["discount_amount"])))
            self.bills_table.setItem(row_idx, 6, QTableWidgetItem(rupees(b["total"])))

            remove_btn = QPushButton("Remove")
            remove_btn.setProperty("role", "danger")
            remove_btn.setProperty("compact", "true")
            bill_id = b["id"]
            remove_btn.clicked.connect(lambda _, bid=bill_id, no=b["bill_no"]: self._delete_bill(bid, no))
            self.bills_table.setCellWidget(row_idx, 7, remove_btn)

            total_revenue += b["total"]
            total_pieces += b["piece_count"]
        self.bills_table.resizeRowsToContents()

        self.summary_label.setText(
            f"{len(bills)} bill(s) \u2022 {total_pieces} piece(s) sold \u2022 {rupees(total_revenue)} total"
        )

    def _view_bill(self):
        rows = self.bills_table.selectionModel().selectedRows()
        if not rows:
            return
        bill_id = self._bills_cache[rows[0].row()]["id"]
        bill_row, bill_items = self.db.get_bill(bill_id)
        dialog = ReceiptDialog(bill_row, bill_items, self)
        dialog.exec()

    def _delete_bill(self, bill_id, bill_no):
        confirm = QMessageBox.question(
            self, "Remove Bill",
            f"Remove bill '{bill_no}'? This cannot be undone."
        )
        if confirm != QMessageBox.Yes:
            return
        if not confirm_delete_password(self, f"remove bill '{bill_no}'"):
            return
        self.db.delete_bill(bill_id)
        self.refresh()

    def _export_csv(self):
        if not self._bills_cache:
            QMessageBox.information(self, "Nothing to export", "No bills match the current filter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Sales to CSV", "sales_export.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Bill No", "Date", "Customer", "Phone", "Pieces", "Subtotal", "Discount", "Total"])
            for b in self._bills_cache:
                writer.writerow([
                    b["bill_no"], b["bill_date"], b["customer_name"] or "Walk-in",
                    b["customer_phone"] or "", b["piece_count"], b["subtotal"],
                    b["discount_amount"], b["total"],
                ])
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
