# Cloth Shop Billing

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
