@echo off
echo ========================================
echo   CryptoTrade Pro - Advanced Trading Bot
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python detected
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
    echo.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM Install/upgrade dependencies
echo [INFO] Installing/verifying dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r trade_bot\requirements.txt
echo [OK] Dependencies installed
echo.

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo [INFO] Creating default .env file...
    (
        echo # Exchange API Keys (Leave empty for paper trading)
        echo BINANCE_API_KEY=
        echo BINANCE_API_SECRET=
        echo NOBITEX_API_KEY=
        echo NOBITEX_API_SECRET=
        echo.
        echo # AI Configuration
        echo OPENAI_API_KEY=
        echo OPENAI_ENDPOINT=https://api.openai.com/v1
        echo.
        echo # Trading Settings
        echo PAPER_TRADING=true
        echo INITIAL_CAPITAL=10000
        echo RISK_LEVEL=medium
    ) > .env
    echo [OK] .env file created - Please configure your API keys
    echo.
)

REM Start the web server
echo ========================================
echo   Starting Web Interface
echo ========================================
echo.
echo Access the dashboard at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

cd trade_bot\web
python server.py

pause
