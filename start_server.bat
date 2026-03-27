@echo off
:: AI Interview Preparation Platform - Stage 2 Startup Script (Windows)
:: This script sets up and starts the Stage 2 backend server

setlocal EnableDelayedExpansion

echo 🚀 AI Interview Preparation Platform - Stage 2
echo ===============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% found

:: Check if we're in the right directory
if not exist "backend" (
    echo [ERROR] This script must be run from the project root directory (where backend\ folder is located)
    pause
    exit /b 1
)

:: Check if virtual environment exists, create if not
if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [SUCCESS] Dependencies installed

:: Check if .env file exists
if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] .env file not found. Creating from .env.example...
        copy ".env.example" ".env" >nul
        echo [WARNING] Please edit .env file and add your GROQ_API_KEY before starting the server
        echo.
        echo To edit the .env file:
        echo   notepad .env
        echo   or
        echo   code .env
        echo.
        pause
    ) else (
        echo [ERROR] .env file not found and .env.example doesn't exist
        echo Please create a .env file with FEATHERLESS_API_KEY=your_key_here
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] .env file found
)

:: Parse .env file to check API key (simple check)
set "API_KEY_SET="
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if "%%a"=="GROQ_API_KEY" (
        if not "%%b"=="" (
            if not "%%b"=="your_groq_api_key_here" (
                set "API_KEY_SET=1"
            )
        )
    )
)

if not defined API_KEY_SET (
    echo [ERROR] GROQ_API_KEY not set in .env file
    echo Please edit .env and add your Groq API key
    pause
    exit /b 1
)

echo [SUCCESS] GROQ_API_KEY is configured

:: Start the server
echo [INFO] Starting the Stage 2 backend server...
echo.
echo 🌐 Server will be available at:
echo    • API: http://localhost:8000
echo    • Docs: http://localhost:8000/docs
echo    • Health: http://localhost:8000/health
echo.
echo 📖 To test the API, run in another terminal:
echo    python example_usage.py
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
python main.py

pause