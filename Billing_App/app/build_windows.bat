@echo off
echo ============================================
echo  Cloth Shop Billing System - Build .exe
echo ============================================
echo.

echo Step 1/3: Installing required packages...
pip install -r requirements.txt
pip install -r ..\clothshop_billing_server\backend\requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo.
    echo Something went wrong installing packages. Make sure Python is
    echo installed and added to PATH, then try again.
    pause
    exit /b 1
)

echo.
echo Step 2/3: Building ClothShopBilling.exe (this can take a minute)...
rem Bug fix: this build used to only bundle assets\, which is why the
rem Application Status tab's "Start Server" button failed once the app
rem was packaged as a .exe -- the whole clothshop_billing_server folder
rem (the FastAPI backend + the web frontend it serves to phones) was
rem never inside the .exe at all, and uvicorn's dynamic protocol/loop
rem imports aren't picked up by PyInstaller's static analysis unless
rem named explicitly below, so even with the folder bundled the server
rem would previously have failed on import. Both are fixed by the
rem --add-data and --hidden-import flags below; main.py now knows what
rem to do with a bundled clothshop_billing_server folder when it's
rem launched with --run-server (see main.py's run_embedded_server()).
pyinstaller --noconsole --onefile --name ClothShopBilling ^
    --icon=assets\icon.ico ^
    --add-data "assets;assets" ^
    --add-data "..\clothshop_billing_server;clothshop_billing_server" ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    main.py
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
echo (The database is untouched by this build -- it still lives at
echo  %%USERPROFILE%%\.cloth_shop_billing\cloth_shop.db and both the
echo  desktop app and the on/off server inside it share that one file.)
echo.
pause
