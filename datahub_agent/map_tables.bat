@echo off
REM Data Hub - Χαρτογράφηση πινάκων Epsilon (read-only)
cd /d "%~dp0"
py map_tables.py
echo.
pause
