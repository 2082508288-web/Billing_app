# Desktop app guide

## Setup and launch

From the repository root, with Python 3.9+:

```sh
python -m pip install -r app/requirements.txt
python app/main.py
```

From this folder, use `python -m pip install -r requirements.txt` and `python main.py`.

## Shop workflow

| Tab | Purpose |
| --- | --- |
| New Bill | Scan or enter products, apply discounts, record the amount paid, then save and print an invoice. |
| Inventory | Maintain categories, brands, prices, and stock. |
| Customers | Customer details, purchase history, receipt reprints, and requests for future purchases. |
| Payments & Balances | All bills and payments, including walk-in sales. Select an account to view its ledger or receive an outstanding payment. |
| Expenses | Business expenses with date and category filters. |
| Sales History | Search bills, filter by day or month range, reprint receipts, and export CSV. |
| Statistics | Revenue, collections, expenses, credit, daily bars, monthly sales, and best sellers. |
| Data & Backups | Local database location, database backup, and export of all tables as CSV. |

A saved bill appears in Sales History and Payments & Balances before the receipt opens. Saving a backdated bill expands the Sales History date range and clears its search so the new entry is visible. Statistics switches to All time when the saved bill is outside the current period. Later payments, bill removals, and other committed changes refresh the reports automatically.

Paid now defaults to the bill total. Enter a smaller amount for partial payment or zero for credit. Unpaid balances remain unpaid when the app restarts. No payment is recorded merely because a receipt or QR is generated.

Sales History opens with All time selected. Manual date changes select Custom; use Search (or Enter in the search box) to apply them. Day/month shortcuts apply immediately.

The daily chart starts with the last seven days. It includes days with zero sales, and averages use calendar days. Longer periods scroll horizontally; periods longer than 90 days show the latest 90 daily bars, with a caption explaining that limit. The KPI cards use the entire selected period. The monthly chart always shows the complete history.

## Receipt and payment QR

QR codes are generated locally using `qrcode[pil]`, which is included in the requirements and Windows build. They appear in the receipt preview and exported PDF.

Edit the shop identity, bank details, and `UPI_ID` in `receipt.py` to match the shop. The existing configured UPI address is retained; confirm it belongs to the receiving account before collecting live payments. Partially paid receipts encode only the outstanding amount. Paid receipts are labelled PAID and retain a merchant QR without a requested amount.

Use Print A4 or Save as PDF from the receipt window. If opening a receipt fails after a sale is saved, reopen that bill from Sales History; the cart has already been cleared to prevent accidental duplicate submission.

## Local data and backup

Data remains at the existing location:

- Windows: `%USERPROFILE%\.cloth_shop_billing\cloth_shop.db`
- macOS/Linux: `~/.cloth_shop_billing/cloth_shop.db`

Use **Data & Backups → Back Up Database** to create a consistent snapshot while the app is running. Backups are saved in a `backups` directory alongside the database. Copy these backups to a separate device for safekeeping. CSV export is useful for reports; the database backup preserves the complete relational data.

The consolidation and server removal do not move or reset shop records. Databases from before the payment ledger are migrated once. Existing payment records are preserved; erroneous payment rows that an earlier version may already have created cannot be identified reliably and require reconciliation against shop records.

## Windows executable

Run `build_windows.bat` on Windows. It changes to this folder, installs desktop dependencies, and builds `dist/ClothShopBilling.exe` using PyInstaller. No Python installation is needed on the computer running the finished executable.

## Source layout

- `main.py`: entry point, tab wiring, and refresh scheduling
- `database.py`: SQLite schema, migrations, transactions, reporting, backup/export
- `billing_tab.py`, `sales_tab.py`, `balances_tab.py`: bills and payments
- `customers_tab.py`, `inventory_tab.py`, `expenses_tab.py`: shop records
- `stats_tab.py`: charts and summary cards
- `receipt.py`: invoice layout, QR, printing, and PDF
- `status_tab.py`: local data and backup page
- `theme.py`, `widgets.py`: shared visual styling and controls
- `assets/`: application icons

Categories and brands are editable data. Manual products are saved to the catalog for reuse. Removing a bill/customer requires confirmation and the existing password defined by `DELETE_PASSWORD` in `widgets.py`.
