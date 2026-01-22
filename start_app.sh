#!/bin/bash
# QuantDSF v2 Startup Script for Git Bash/Linux/Mac
# ==================================================

echo ""
echo "============================================================"
echo "  QuantDSF v2 - nanoDSF Analysis Platform"
echo "  Starting application..."
echo "============================================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start the application on port 9050
python app_v2.py --port 9050 --host 127.0.0.1
