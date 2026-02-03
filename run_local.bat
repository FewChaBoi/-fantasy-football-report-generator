@echo off
echo Fantasy Football Report Generator - Local Development
echo =====================================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r backend\requirements.txt -q

REM Check for .env file
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and add your Yahoo OAuth credentials.
    echo.
    copy .env.example .env
    echo Created .env file - please edit it with your credentials.
    pause
    exit /b 1
)

REM Run the server
echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop
echo.
cd backend
python main.py
