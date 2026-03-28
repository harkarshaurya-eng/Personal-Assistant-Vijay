@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    set "VIJAY_PYTHON=python"
    set "VIJAY_PYTHON_LABEL=system python"
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3.12 -c "import sys" >nul 2>nul
        if %errorlevel%==0 (
            set "VIJAY_PYTHON=py -3.12"
            set "VIJAY_PYTHON_LABEL=Python 3.12"
        ) else (
            py -3.11 -c "import sys" >nul 2>nul
            if %errorlevel%==0 (
                set "VIJAY_PYTHON=py -3.11"
                set "VIJAY_PYTHON_LABEL=Python 3.11"
            ) else (
                set "VIJAY_PYTHON=py -3"
                set "VIJAY_PYTHON_LABEL=default py launcher"
            )
        )
    )
    echo Creating Vijay virtual environment with %VIJAY_PYTHON_LABEL%...
    call %VIJAY_PYTHON% -m venv .venv
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
echo The first voice enrollment may take extra time because Vijay downloads local speech models.
python -c "import sys; print(f'Using Python {sys.version.split()[0]} for Vijay.')"
echo.

python main.py
