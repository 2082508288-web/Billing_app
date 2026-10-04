# Cloth Shop Billing

A local desktop billing app built with PySide6 and SQLite. No backend service, browser server, or messaging integration is required.

## Run

Requires Python 3.9 or newer.

```sh
python -m pip install -r app/requirements.txt
python app/main.py
```

The maintained source is in **`app/`**. The old `Billing_App/app/main.py` launcher and `Billing_App/setup.bat` forward to this app, so there is only one implementation to maintain.

## Build for Windows

On Windows, run `app/build_windows.bat`. The executable is created at `app/dist/ClothShopBilling.exe`. The build includes local QR generation and does not bundle a server.

See [the app guide](app/README.md) for billing, payments, charts, and backups.

## Regression checks

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

Tests use temporary databases and synthetic records. They cover credit persistence, old-schema upgrades, walk-in payments, bill-to-report refresh, chart dates, receipt QR/PDF generation, backups, and transaction rollback.
