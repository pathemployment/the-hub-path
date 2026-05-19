@echo off
REM Re-run the Job Bank scrape + inspection in one shot.
call .venv\Scripts\activate.bat
python -m src.main --skip-wpb --skip-employers --skip-msform
echo.
echo ===== INSPECT RESULTS =====
python inspect_last_run.py
