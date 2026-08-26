#!/bin/bash

echo "========================================"
echo "  CryptoTrade Pro - Advanced Trading Bot"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed or not in PATH"
    echo "Please install Python 3.8+ using your package manager"
    exit 1
fi

echo "[OK] Python detected: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    echo "[OK] Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate
echo "[OK] Virtual environment activated"
echo ""

# Install/upgrade dependencies
echo "[INFO] Installing/verifying dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r trade_bot/requirements.txt
echo "[OK] Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "[INFO] Creating default .env file..."
    cat > .env << EOF
# Exchange API Keys (Leave empty for paper trading)
BINANCE_API_KEY=
BINANCE_API_SECRET=
NOBITEX_API_KEY=
NOBITEX_API_SECRET=

# AI Configuration
OPENAI_API_KEY=
OPENAI_ENDPOINT=https://api.openai.com/v1

# Trading Settings
PAPER_TRADING=true
INITIAL_CAPITAL=10000
RISK_LEVEL=medium
EOF
    echo "[OK] .env file created - Please configure your API keys"
    echo ""
fi

# Start the web server
echo "========================================"
echo "  Starting Web Interface"
echo "========================================"
echo ""
echo "Access the dashboard at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd trade_bot/web
python server.py
