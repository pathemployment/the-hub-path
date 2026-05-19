@echo off
REM Weekly Job Report Pipeline - Windows Task Scheduler entry point.
REM Runs weekly via Task Scheduler. Writes data/jobs.js to the Hub repo and pushes.

cd /d "%~dp0"
set FIRECRAWL_API_KEY=
call .venv\Scripts\activate.bat
python -m src.main --prod --push >> data\run-log.txt 2>&1
deactivate