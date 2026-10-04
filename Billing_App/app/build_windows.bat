@echo off
call "%~dp0..\..\app\build_windows.bat"
exit /b %errorlevel%
