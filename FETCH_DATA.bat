@echo off
title Fetch SEO Data
color 0A
cd /d "%~dp0"
echo.
echo  ============================================
echo    FETCHING FRESH SEO DATA
echo  ============================================
echo.
echo  Fetching 28 days of data from Google...
echo.
python main.py
echo.
echo  ============================================
echo  Done! Open dashboard to see updated data.
echo  ============================================
echo.
pause
