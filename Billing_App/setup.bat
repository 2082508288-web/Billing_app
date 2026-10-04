@echo off
echo ================================================================
echo  Cloth Shop Billing System - Full Setup
echo ================================================================
echo.
echo This installs everything needed to run and package the app,
echo straight into your normal Python installation (no virtual
echo environment is created, on purpose).
echo.
echo It does NOT touch your shop's existing database. The database
echo always lives at:
echo    %%USERPROFILE%%\.cloth_shop_billing\cloth_shop.db
echo The desktop app reads and writes that file. This script does
echo not create, move, or reset it.
echo.
pause

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.10+ from https://python.org and tick
    echo "Add python.exe to PATH" during install, then run this again.
    pause
    exit /b 1
)

echo.
echo Step 1/2: Installing the desktop app's dependencies...
pip install -r app\requirements.txt
if errorlevel 1 goto :pipfail

echo.
echo Step 2/2: Building ClothShopBilling.exe...
pip install pyinstaller
if errorlevel 1 goto :pipfail

cd app
call build_windows.bat
cd ..

echo.
echo ================================================================
echo  Setup complete.
echo ================================================================
echo.
echo Your app is at:  app\dist\ClothShopBilling.exe
echo Copy that one file to the shop's desktop.
echo.
echo Your existing data (if any) at
echo    %%USERPROFILE%%\.cloth_shop_billing\cloth_shop.db
echo was not touched by this script and will be picked up
echo automatically the first time the app runs.
echo.
echo Tip: use the "Backup Database Now" and "Export Whole Database
echo (CSV)" buttons on the Application Status tab any time you want a
echo safety copy of your data.
echo.
pause
exit /b 0

:pipfail
echo.
echo Something went wrong installing packages above. Scroll up to see
echo the error, fix it (often just re-running as Administrator, or
echo checking your internet connection), then run setup.bat again.
pause
exit /b 1
