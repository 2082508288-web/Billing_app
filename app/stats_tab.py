"""
stats_tab.py
------------
Business insights: top-selling items, daily sales trend with mean/std-dev,
category breakdown, and customer preferences (top spenders + open "wants
next" requests across all customers).
"""

import statistics
from datetime import date
from matplotlib.ticker import FuncFormatter, MaxNLocator

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDateEdit,
    QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from widgets import rupees, make_heading, make_stat_card
from theme import COLORS


class StatsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        outer_scroll.setWidget(container)

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        page.addWidget(outer_scroll)

        outer = QVBoxLayout(container)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(make_heading("Statistics", "Sales trends, best sellers, and what customers want"))
        header_row.addStretch()

        self.quick_range_combo = QComboBox()
        self.quick_range_combo.addItems(["Last 7 days", "Last 30 days", "This month", "All time"])
        self.quick_range_combo.currentTextChanged.connect(self.refresh)
        header_row.addWidget(QLabel("Period:"))
        header_row.addWidget(self.quick_range_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("role", "secondary")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        outer.addLayout(header_row)

        # ---------------- KPI cards ----------------
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(10)
        outer.addLayout(self.kpi_grid)

        # ---------------- charts row ----------------
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)


        trend_box = QGroupBox("Daily Sales")
        trend_v = QVBoxLayout(trend_box)
        self.trend_figure = Figure(figsize=(6, 3.6), constrained_layout=True)
        self.trend_canvas = FigureCanvas(self.trend_figure)
        self.trend_canvas.setMinimumHeight(300)
        self.trend_caption = QLabel()
        self.trend_caption.setProperty("role", "subheading")
        trend_v.addWidget(self.trend_caption)
        self.trend_scroll = QScrollArea()
        self.trend_scroll.setWidgetResizable(True)
        self.trend_scroll.setWidget(self.trend_canvas)
        self.trend_scroll.setMinimumHeight(340)
        trend_v.addWidget(self.trend_scroll)
        outer.addWidget(trend_box)
        outer.addLayout(charts_row)

        category_box = QGroupBox("Sales by Category")
        category_v = QVBoxLayout(category_box)
        self.category_figure = Figure(figsize=(4.2, 3.6), constrained_layout=True)
        self.category_canvas = FigureCanvas(self.category_figure)
        self.category_canvas.setMinimumHeight(300)
        category_v.addWidget(self.category_canvas)
        charts_row.addWidget(category_box, 1)

        # ---------------- monthly sales bar chart ----------------
        # Bug fix: stat_monthly_sales() already existed in database.py
        # (its docstring even says "Used for the Monthly Sales chart"),
        # but no chart was ever actually built for it in this tab -- the
        # daily trend chart above only covers the selected Period filter
        # and gets unreadable over a long "All time" range. This is a
        # separate, always-full-history monthly view.
        monthly_box = QGroupBox("Monthly Sales (all-time)")
        monthly_v = QVBoxLayout(monthly_box)
        self.monthly_figure = Figure(figsize=(10, 3.2), constrained_layout=True)
        self.monthly_canvas = FigureCanvas(self.monthly_figure)
        self.monthly_canvas.setMinimumHeight(260)
        monthly_v.addWidget(self.monthly_canvas)
        charts_row.addWidget(monthly_box, 2)

        # ---------------- top items ----------------
        top_items_box = QGroupBox("Best Selling Items")
        top_items_v = QVBoxLayout(top_items_box)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Rank by:"))
        self.top_items_sort_combo = QComboBox()
        self.top_items_sort_combo.addItems(["Quantity sold", "Revenue"])
        self.top_items_sort_combo.currentTextChanged.connect(self.refresh)
        sort_row.addWidget(self.top_items_sort_combo)
        sort_row.addStretch()
        top_items_v.addLayout(sort_row)

        self.top_items_table = QTableWidget(0, 4)
        self.top_items_table.setHorizontalHeaderLabels(["Item", "Category", "Qty Sold", "Revenue"])
        self.top_items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.top_items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.top_items_table.setMinimumHeight(260)
        top_items_v.addWidget(self.top_items_table)
        outer.addWidget(top_items_box)

        # ---------------- customer preferences ----------------
        pref_row = QHBoxLayout()
        pref_row.setSpacing(12)
        outer.addLayout(pref_row)

        top_customers_box = QGroupBox("Top Customers")
        tc_v = QVBoxLayout(top_customers_box)
        self.top_customers_table = QTableWidget(0, 3)
        self.top_customers_table.setHorizontalHeaderLabels(["Name", "Visits", "Total Spent"])
        self.top_customers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.top_customers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.top_customers_table.setMinimumHeight(220)
        tc_v.addWidget(self.top_customers_table)
        pref_row.addWidget(top_customers_box, 1)

        wishlist_box = QGroupBox("What Customers Are Asking For (open requests)")
        wl_v = QVBoxLayout(wishlist_box)
        self.wishlist_table = QTableWidget(0, 3)
        self.wishlist_table.setHorizontalHeaderLabels(["Customer", "Wants", "Since"])
        self.wishlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.wishlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.wishlist_table.setMinimumHeight(220)
        wl_v.addWidget(self.wishlist_table)
        pref_row.addWidget(wishlist_box, 1)

    # ------------------------------------------------------------- helpers
    def _date_range(self):
        today = QDate.currentDate()
        label = self.quick_range_combo.currentText()
        if label == "Last 7 days":
            frm = today.addDays(-6)
        elif label == "This month":
            frm = QDate(today.year(), today.month(), 1)
        elif label == "All time":
            first = self.db.first_bill_date()
            frm = QDate.fromString(first, "yyyy-MM-dd") if first else today
        else:  # Last 30 days
            frm = today.addDays(-29)
        return frm.toString("yyyy-MM-dd"), today.toString("yyyy-MM-dd")

    def refresh(self):
        date_from, date_to = self._date_range()
        self._refresh_kpis(date_from, date_to)
        self._refresh_trend_chart(date_from, date_to)
        self._refresh_category_chart(date_from, date_to)
        self._refresh_monthly_chart()
        self._refresh_top_items(date_from, date_to)
        self._refresh_top_customers(date_from, date_to)
        self._refresh_wishlist()

    def _clear_grid(self):
        while self.kpi_grid.count():
            child = self.kpi_grid.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()

    def _refresh_kpis(self, date_from, date_to):
        self._clear_grid()
        totals = self.db.stat_totals(date_from, date_to)
        daily = self.db.stat_daily_sales(date_from, date_to)
        revenues = [d["revenue"] for d in daily]
        mean_daily = statistics.mean(revenues) if revenues else 0
        std_daily = statistics.pstdev(revenues) if len(revenues) > 1 else 0

        cards = [
            make_stat_card(
                "Total Revenue",
                rupees(totals["revenue"]),
                f"{totals['bill_count']} bill(s)",
            ),
            make_stat_card(
                "Total Expenses",
                rupees(totals["expenses"]),
                "business costs in period",
            ),
            make_stat_card(
                "Net Profit",
                rupees(totals["net_profit"]),
                "Revenue − Expenses",
            ),
            make_stat_card(
                "Payments Collected",
                rupees(totals["payments_collected"]),
                "cash/credit payments received",
            ),
            make_stat_card(
                "Outstanding Credit",
                rupees(totals["outstanding"]),
                "unpaid balance",
            ),
            make_stat_card("Pieces Sold", str(totals["pieces"]), ""),
            make_stat_card("Avg Bill Value", rupees(totals["avg_bill"]), ""),
            make_stat_card(
                "Mean Daily Sales",
                rupees(mean_daily),
                f"over {len(revenues)} calendar day(s)",
            ),
            make_stat_card(
                "Std. Dev. (daily)",
                rupees(std_daily),
                "day-to-day variation",
            ),
        ]

        # Keep the financial KPIs together at the top, then operational KPIs.
        columns = 3
        for index, card in enumerate(cards):
            self.kpi_grid.addWidget(card, index // columns, index % columns)

    @staticmethod
    def _style_axes(ax):
        ax.set_facecolor("white")
        for edge in ("top", "right", "left"):
            ax.spines[edge].set_visible(False)
        ax.spines["bottom"].set_color(COLORS["border"])
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=COLORS["border"], linewidth=0.6, alpha=0.7)
        ax.tick_params(axis="both", length=0, labelsize=9, colors=COLORS["muted"], pad=8)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.set_ylabel("Revenue (Rs.)", color=COLORS["muted"], fontsize=9)

    def _refresh_trend_chart(self, date_from, date_to):
        daily = self.db.stat_daily_sales(date_from, date_to)
        # Keep individual days legible over long histories; KPIs still use the full range.
        visible = daily[-90:]
        self.trend_caption.setText(
            ("Latest 90 days of this period · " if len(daily) > 90 else "")
            + "One bar per day · includes days with no sales"
        )
        self.trend_canvas.setMinimumWidth(max(600, len(visible) * 34))
        self.trend_figure.clear()
        ax = self.trend_figure.add_subplot(111)
        self._style_axes(ax)
        revenues = [row["revenue"] for row in visible]
        dates = [date.fromisoformat(row["d"]) for row in visible]
        positions = list(range(len(visible)))
        bars = ax.bar(positions, revenues, width=0.58, color=COLORS["primary"], zorder=3)
        ax.set_xticks(positions, [day.strftime("%a\n%d %b") if len(visible) <= 7
                                 else day.strftime("%d\n%b") for day in dates])
        ax.set_xlim(-0.7, max(len(visible) - 0.3, 0.7))
        maximum = max(revenues, default=0)
        ax.set_ylim(0, maximum * 1.25 if maximum else 1)
        if maximum:
            mean = statistics.mean(revenues)
            ax.axhline(mean, color=COLORS["accent"], linestyle="--", linewidth=1.2,
                       label=f"Daily average: {rupees(mean)}")
            ax.legend(loc="upper left", fontsize=8, frameon=False)
            if len(visible) <= 7:
                ax.bar_label(bars, labels=[f"{value:,.0f}" if value else "0" for value in revenues],
                             padding=5, fontsize=9, color=COLORS["text"])
        else:
            ax.text(0.5, 0.5, "No sales recorded in this period", transform=ax.transAxes,
                    ha="center", color=COLORS["muted"])
        self.trend_canvas.draw()

    def _refresh_category_chart(self, date_from, date_to):
        rows = self.db.stat_category_sales(date_from, date_to)
        self.category_figure.clear()
        ax = self.category_figure.add_subplot(111)
        if rows and sum(r["revenue"] for r in rows) > 0:
            labels = [r["category"] or "Uncategorised" for r in rows]
            values = [r["revenue"] for r in rows]
            palette = [COLORS["primary"], COLORS["accent"], "#4a90a4", "#8e6c88", "#c4a35a", "#7a8b69"]
            colors = [palette[i % len(palette)] for i in range(len(labels))]
            # Percentage stays on the wedge; category names move to a side
            # legend instead of wedge labels, which overlap badly when one
            # category dominates (e.g. a single 100% slice).
            wedges, _texts, _autotexts = ax.pie(
                values, autopct="%1.0f%%", colors=colors,
                textprops={"fontsize": 8, "color": "white", "fontweight": "bold"},
                pctdistance=0.75,
            )
            ax.legend(
                wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
                fontsize=8, frameon=False,
            )
        else:
            ax.text(0.5, 0.5, "No sales in this period", ha="center", va="center", color=COLORS["muted"])
            ax.set_xticks([])
            ax.set_yticks([])
        self.category_canvas.draw()

    def _refresh_monthly_chart(self):
        rows = self.db.stat_monthly_sales()
        self.monthly_figure.clear()
        ax = self.monthly_figure.add_subplot(111)
        self._style_axes(ax)
        if rows:
            months = [r["month"] for r in rows]
            revenues = [r["revenue"] or 0 for r in rows]
            bars = ax.bar(months, revenues, color=COLORS["primary"], alpha=0.9)
            step = max(1, (len(months) + 11) // 12)
            ax.set_xticks(range(0, len(months), step), months[::step])
            ax.set_ylim(0, max(max(revenues) * 1.25, 1))
            ax.tick_params(axis="x", rotation=30, labelsize=8)
            ax.tick_params(axis="y", labelsize=8)
            # Label each bar with its bill count so this chart also
            # answers "how many bills that month", not just revenue.
            for bar, r in list(zip(bars, rows))[::step]:
                ax.annotate(
                    f"{r['bill_count']}",
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                    color=COLORS["muted"],
                )
        else:
            ax.text(0.5, 0.5, "No sales yet", ha="center", va="center", color=COLORS["muted"])
            ax.set_xticks([])
            ax.set_yticks([])
        self.monthly_canvas.draw()

    def _refresh_top_items(self, date_from, date_to):
        by = "quantity" if self.top_items_sort_combo.currentText() == "Quantity sold" else "revenue"
        rows = self.db.stat_top_items(date_from, date_to, limit=10, by=by)
        self.top_items_table.setRowCount(len(rows))
        for row_idx, r in enumerate(rows):
            self.top_items_table.setItem(row_idx, 0, QTableWidgetItem(r["name"]))
            self.top_items_table.setItem(row_idx, 1, QTableWidgetItem(r["category"] or "-"))
            self.top_items_table.setItem(row_idx, 2, QTableWidgetItem(str(r["total_qty"])))
            self.top_items_table.setItem(row_idx, 3, QTableWidgetItem(rupees(r["total_revenue"])))
            if row_idx == 0:
                for col in range(4):
                    self.top_items_table.item(row_idx, col).setBackground(QColor("#fff3cd"))

    def _refresh_top_customers(self, date_from, date_to):
        rows = self.db.stat_top_customers(date_from, date_to, limit=10)
        self.top_customers_table.setRowCount(len(rows))
        for row_idx, r in enumerate(rows):
            self.top_customers_table.setItem(row_idx, 0, QTableWidgetItem(r["name"]))
            self.top_customers_table.setItem(row_idx, 1, QTableWidgetItem(str(r["visits"])))
            self.top_customers_table.setItem(row_idx, 2, QTableWidgetItem(rupees(r["total_spent"])))

    def _refresh_wishlist(self):
        rows = self.db.all_open_wishlist()
        self.wishlist_table.setRowCount(len(rows))
        for row_idx, r in enumerate(rows):
            self.wishlist_table.setItem(row_idx, 0, QTableWidgetItem(r["customer_name"]))
            self.wishlist_table.setItem(row_idx, 1, QTableWidgetItem(r["item_description"]))
            self.wishlist_table.setItem(row_idx, 2, QTableWidgetItem(r["date_added"][:10]))
