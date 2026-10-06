#!/usr/bin/env bash
# Day 9 - React Product Dashboard & Shopping Cart Starter
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "===================================================="
echo " ShopDash - React Product Dashboard & Shopping Cart"
echo " Day 9 Implementation"
echo "===================================================="

# 1. Virtual Environment Setup
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 2. Database Migrations & Seed
echo "Applying database migrations..."
python backend/manage.py migrate --noinput

echo "Seeding products..."
python backend/manage.py seed_products

# 3. Check / Build frontend if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install --prefix frontend
fi

echo "Building production frontend bundle..."
npm run build --prefix frontend

echo "----------------------------------------------------"
echo "Available run options:"
echo " 1) Run both Django Backend (8000) and Vite Dev Server (5173)"
echo " 2) Run Django Backend only (http://127.0.0.1:8000 - serves API & built UI)"
echo " 3) Run Vite Dev Server only (http://localhost:5173)"
echo "----------------------------------------------------"

MODE="${1:-1}"

if [ "$MODE" = "2" ]; then
    echo "Starting Django server on http://127.0.0.1:8000..."
    python backend/manage.py runserver 127.0.0.1:8000
elif [ "$MODE" = "3" ]; then
    echo "Starting Vite dev server on http://localhost:5173..."
    npm run dev --prefix frontend
else
    echo "Starting Django API server in background on http://127.0.0.1:8000..."
    python backend/manage.py runserver 127.0.0.1:8000 &
    DJANGO_PID=$!

    cleanup() {
        echo ""
        echo "Shutting down servers..."
        kill $DJANGO_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup SIGINT SIGTERM EXIT

    echo "Starting Vite frontend dev server on http://localhost:5173..."
    npm run dev --prefix frontend -- --host
fi
