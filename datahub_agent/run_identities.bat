@echo off
REM Data Hub Agent - hourly identities sync (Tier A) - Task Scheduler
cd /d "%~dp0"
echo ============================================ >> agent_log.txt
echo Run (identities): %date% %time% >> agent_log.txt
py agent.py --tier A >> agent_log.txt 2>&1
echo (finished %date% %time%) >> agent_log.txt
