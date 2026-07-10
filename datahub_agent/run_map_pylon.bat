@echo off
chcp 65001 >nul
REM Data Hub - Χαρτογραφηση βασης Pylon (read-only). Θελει PYLON_CONN στο .env.
cd /d "%~dp0"
py map_pylon.py
echo.
pause
