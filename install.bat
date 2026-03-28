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
echo Vijay is starting.
echo Add Google, Groq, and Supabase keys in .env for the full experience.
echo.

python main.py
