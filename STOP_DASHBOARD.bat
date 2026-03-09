@echo off
title Stop SEO Dashboard
echo.
echo  Stopping SEO Dashboard...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM python.exe >nul 2>&1
echo  Dashboard stopped.
timeout /t 2 /nobreak >nul
exit
