@echo off
title SEO Dashboard — best4juniors.nl
color 0F
cls

echo.
echo  ============================================
echo    SEO AI DASHBOARD
echo    best4juniors.nl
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Install from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH"
    pause
    exit /b
)

:: Go to script folder
cd /d "%~dp0"

:: Install packages silently if needed
echo  Checking packages...
pip install -r requirements.txt -q --disable-pip-version-check

:: Kill any old dashboard on port 5000
echo  Starting dashboard...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Fetch fresh data in background
start /B python main.py

:: Wait 3 seconds then open browser
timeout /t 3 /nobreak >nul
start http://localhost:5000

:: Start dashboard (hidden-style: minimized)
start /MIN "" python dashboard.py

echo.
echo  Dashboard is running at http://localhost:5000
echo  Browser should open automatically.
echo  Close this window when done.
echo.
echo  ============================================
echo.
timeout /t 5 /nobreak >nul
exit
