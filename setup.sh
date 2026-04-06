#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Contrarian Investing Platform Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install Python 3.12+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PYTHON_VERSION"

# Check Node
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Install Node.js 18+."
    exit 1
fi
echo "Node: $(node --version)"

# Python venv + deps
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "Initializing SQLite database..."
python3 -c "from backend.database import init_db; init_db()"

# Frontend
echo "Installing frontend dependencies..."
cd frontend
npm install --silent
echo "Building frontend..."
npm run build
cd ..

echo ""
echo "=== Setup complete! ==="
echo "Run ./start.sh to launch the app."
