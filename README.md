# Cloth Shop Billing

## Employee and admin dashboards

The app opens in **Employee** mode: existing catalog items, fixed prices, quantities,
customer details, full payment and receipts. GST is automatically included in the
amount due using the existing calculation: a ₹100 price with 5% GST totals ₹105.

**Admin login** unlocks discounts, partial payments, credit, inventory, customers,
balances, expenses, sales history, statistics, and the backup/export tools available
in the recommended copy. **Lock admin / Employee mode** clears the unfinished bill
and returns to employee access. Restarting always begins in Employee mode.

The admin password configured for this release also authorizes deletion confirmations.
The local application access gate does not replace Windows account/file permissions
for protecting the SQLite database or preventing edits to the program itself.

## Windows: install and build

1. Install **standard 64-bit Python 3.13** from [python.org](https://www.python.org/downloads/windows/), including the Python launcher. Supported: Windows 10/11 x64, CPython 3.10–3.14. Free-threaded Python, 32-bit Python and ARM64 Python are not supported by this build path.
2. Clone the repository, or download and **extract the complete ZIP** into a folder you can write to. Keep the `tools` folder with the application folders.
3. Double-click **`setup.bat` at the repository root**. Internet is needed to install packages.
4. When it reports success, open **`Billing_App\app\dist\ClothShopBilling.exe`**.

The root setup builds the copy with backup/export tools. `Billing_App\setup.bat`
uses the same setup. To build the alternate root `app` copy, run
`app\build_windows.bat`; its executable is in `app\dist`.

Setup chooses a compatible interpreter, installs packages into that app's
`.venv-windows` folder, checks database/desktop/receipt behavior using temporary
data, and builds the executable. It does not install into your global Python or
require Administrator access. Keep using the same shop Windows account: its data
lives at `%USERPROFILE%\.cloth_shop_billing\cloth_shop.db`.

After pulling updates, close the running billing executable and run setup again.
The app environment is reused when healthy and repaired when the selected Python
changes. Old generated build files and Python caches do not belong in Git.

## If setup fails

The window stays open with a short error. The detailed log is:

- Recommended copy: `Billing_App\app\setup.log`
- Alternate copy: `app\setup.log`

Share that file and the first error, rather than copying thousands of console
lines. Setup stops on the failing step and never reports a failed build as a
success. It requests binary wheels only, so unsupported packages fail clearly
instead of attempting a C/C++ or Rust build.

For a Python detection error, install a supported standard x64 Python and reopen
setup. For package download errors, check your internet/proxy settings. For file
access errors, close the app and place the repository in a writable folder.

Do not delete your `.cloth_shop_billing` data folder to repair setup. An existing
unrecognized `.venv-windows` folder is left alone; rename it if setup asks you to.

## Advanced checks

From Command Prompt at the repository root:

```bat
setup.bat --skip-build
```

This installs dependencies and runs the source smoke checks without creating an
executable. For automation, set `BILLING_NO_PAUSE=1` before invoking a batch file;
every entry point preserves the setup process's exit code.

See [tests/README.md](tests/README.md) for regression commands and historical data
limitations. A native Windows build and packaged-app startup check is still
required before distributing an executable; Linux and wheel-resolution checks
alone do not establish that the packaged Windows application runs.

## Reports and date filters

Sales History, Balances, Expenses and Statistics share these period choices:
Today, Last 7 days, Last 30 days, This month, Selected month, Month range,
Custom dates and All time. Month ranges include both entire months; custom
ranges include both boundary days, including bills with timestamps. All time
includes every recorded date. Select a month to see that month's bills immediately.
Changing a filter refreshes the report; **Apply / Refresh** reloads current data.
Invalid ranges clear the result and prevent an export of stale rows.

CSV exports use the current period and any search/category filter, even if you
haven't pressed Refresh. Balances offers an export of all matched bills and a
separate export of the selected customer's payments. Statistics exports its
summary metrics and the selected period's daily, monthly, product and category
series. CSV is UTF-8 for Excel, with spreadsheet formulas escaped in text fields.

Statistics includes total revenue, expenses, net profit, payments collected,
outstanding credit, bill count, pieces sold, average bill value, and daily mean,
median and population standard deviation. Daily statistics use days with sales,
including days with zero-value bills. Monthly and daily bars use the selected
period. The doughnut chart switches between products and categories; small groups
beyond the top eight are combined as Other.

Definitions:

- Revenue uses bill dates and includes GST. Net profit here means billed revenue
  minus recorded expenses; the app does not track item purchase cost separately.
- Payments collected uses payment dates, including collections on older bills.
- Outstanding means the current unpaid amount on bills issued in the period.
  Balances' "Paid toward these bills" includes later payments too. Its separate
  payment history uses the payment-date filter.
- Product/category revenue allocates each bill's total to its lines, including
  historical bill-level discounts and GST. Allocations retain exact cents so
  chart totals reconcile to billed revenue.

Click a bill row in Balances or Customers' Purchase History to view, print or save
its receipt. Clicking a payment row in Balances opens that payment's bill receipt.
The Balances panes can be resized by dragging their dividers. Receive-payment and
delete buttons keep their own actions. All reporting tools remain admin-only.
