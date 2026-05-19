@echo off
REM Weekly Job Report Pipeline - Windows Task Scheduler entry point.
REM Set this to run weekly (e.g., Monday 6 AM).

cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m src.main --prod >> data\run-log.txt 2>&1
deactivate
