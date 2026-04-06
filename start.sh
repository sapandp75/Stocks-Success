#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo ""
echo "=========================================="
echo "  Contrarian Investing Platform"
echo "  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "=========================================="
echo ""

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
