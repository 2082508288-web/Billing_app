@echo off
cd /d "%~dp0"
echo ============================================
echo  Cloth Shop Billing System - Build .exe
echo ============================================
echo.

echo Step 1/3: Installing required packages...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m pip install pyinstaller
if errorlevel 1 (
    echo.
    echo Something went wrong installing packages. Make sure Python is
    echo installed and added to PATH, then try again.
    pause
    exit /b 1
)

echo.
echo Step 2/3: Building ClothShopBilling.exe (this can take a minute)...
python -m PyInstaller --noconsole --onefile --name ClothShopBilling --icon=assets\icon.ico --add-data "assets;assets" main.py
if errorlevel 1 (
    echo.
    echo The build failed. Scroll up to see the error message.
    pause
    exit /b 1
)

echo.
echo Step 3/3: Done!
echo.
echo Your app is ready at:  dist\ClothShopBilling.exe
echo Copy that file to the shop's desktop and you're good to go.
echo.
pause
