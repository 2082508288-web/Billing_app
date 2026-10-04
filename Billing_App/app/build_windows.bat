@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

echo ============================================
echo  Cloth Shop Billing System - Build .exe
echo ============================================
echo.
echo Step 1/3: Installing required packages...
python -m pip install -r requirements.txt
if errorlevel 1 goto :installfail
python -m pip install pyinstaller
if errorlevel 1 goto :installfail

echo.
echo Step 2/3: Building ClothShopBilling.exe...
python -m PyInstaller --noconsole --onefile --name ClothShopBilling --icon=assets\icon.ico --add-data "assets;assets" main.py
if errorlevel 1 goto :buildfail

echo.
echo Step 3/3: Done!
echo Your app is ready at: dist\ClothShopBilling.exe
popd
pause
exit /b 0

:installfail
echo Package installation failed. Check the error above.
goto :failed

:buildfail
echo The build failed. Check the error above.

:failed
popd
pause
exit /b 1
