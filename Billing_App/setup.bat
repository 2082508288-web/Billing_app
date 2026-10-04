@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1
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
    popd
    pause
    exit /b 1
)

echo.
echo Step 1/2: Installing the desktop app's dependencies...
python -m pip install -r app\requirements.txt
if errorlevel 1 goto :pipfail

echo.
echo Step 2/2: Building ClothShopBilling.exe...
python -m pip install pyinstaller
if errorlevel 1 goto :pipfail

call app\build_windows.bat
if errorlevel 1 goto :buildfail

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
popd
pause
exit /b 0

:pipfail
echo.
echo Something went wrong installing packages above. Scroll up to see
echo the error, fix it (often just re-running as Administrator, or
echo checking your internet connection), then run setup.bat again.
popd
pause
exit /b 1

:buildfail
echo Executable build failed. Setup did not complete.
popd
pause
exit /b 1
