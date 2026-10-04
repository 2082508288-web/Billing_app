# Regression checks

From the repository root, install the chosen desktop copy's requirements, then run:

```bash
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 BILLING_APP_DIR=app python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 BILLING_APP_DIR=Billing_App/app python -m unittest discover -s tests -v
```

Checks use temporary synthetic SQLite databases. The printing flow is exercised
with PDF output instead of a physical printer. No running services are needed.
On Linux, Qt's shared libraries must be available even with the offscreen platform.

Windows release validation also requires running `Billing_App\setup.bat` and
both desktop `build_windows.bat` scripts on Windows. A failed dependency install
or PyInstaller build must return a nonzero exit code and must not print setup
success. Run a packaged executable, print a receipt and save a PDF there as well.

## Existing data

Migration backfill applies only to databases that have never had a payments
table. Existing payments are preserved: the app cannot determine which past
"Migrated from historical bill" entries were correct versus created by the old
bug. Reconcile those entries against shop records if affected.

New bill lines record the actual stock deducted. Old lines lack that information
and retain their historical quantity-based reversal. Original deductions and
invoice numbers already deleted before this update cannot be reconstructed from
the remaining database. The new persistent invoice sequence starts above the
surviving historical invoice numbers and does not decrease after future deletions.

## Windows setup checks

The setup helper has a standard-library unit suite (no Qt required):

```bash
python -m unittest discover -s tests -p test_windows_setup.py -v
```

On Windows, run setup/build through the batch files, execute both full desktop
suites using each app's `.venv-windows\Scripts\python.exe`, and verify that each
packaged main window opens and closes. These checks complement Linux/offscreen
tests; a wheel-resolution check alone does not establish that a Windows
executable runs successfully.

The source startup probe can also be run in a prepared environment:

```bash
python tools/smoke_desktop.py --app-dir Billing_App/app
```

It uses a temporary database and verifies populated startup, tab navigation,
QR generation and PDF output without opening the user's shop database.
