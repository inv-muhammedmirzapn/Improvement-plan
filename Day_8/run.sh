#!/usr/bin/env bash
# OmniStock Quick Start Script
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "===================================================="
echo " OmniStock - Product Management Dashboard"
echo "===================================================="

# Activate Virtual Environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

cd backend

# Run Migrations & Seed
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Seeding products data..."
python manage.py seed_products

echo "----------------------------------------------------"
echo "Starting Django Server on http://127.0.0.1:8000"
echo "Dashboard UI: http://127.0.0.1:8000/"
echo "API Endpoint: http://127.0.0.1:8000/api/products/"
echo "Press Ctrl+C to stop the server."
echo "----------------------------------------------------"

python manage.py runserver 127.0.0.1:8000
