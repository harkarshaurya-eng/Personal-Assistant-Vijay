@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    copy ".env.example" ".env" >nul
)

echo.
echo Vijay is starting on http://127.0.0.1:8000
echo Add your Supabase keys in .env to enable cloud auth and logging.
echo.

python main.py

