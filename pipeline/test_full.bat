@echo off
REM Full pipeline test - all sources, force employer cache refresh.
call .venv\Scripts\activate.bat
python -m src.main --refresh-employers
echo.
echo ===== INSPECT RESULTS =====
python inspect_last_run.py
