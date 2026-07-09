@echo off
REM Data Hub Agent - nightly live sync (τρεχει απο το Task Scheduler)
cd /d "%~dp0"
echo ============================================ >> agent_log.txt
echo Run: %date% %time% >> agent_log.txt
py agent.py --live >> agent_log.txt 2>&1
echo (finished %date% %time%) >> agent_log.txt
