@echo off
REM Test Job Bank + WPB + MS Form (skip employers - they're expensive to refresh).
call .venv\Scripts\activate.bat
python -m src.main --skip-employers
echo.
echo ===== INSPECT RESULTS =====
python inspect_last_run.py
