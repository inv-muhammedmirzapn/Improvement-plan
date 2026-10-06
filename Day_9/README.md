# Day 9 — React Product Dashboard & Shopping Cart

A modern, responsive e-commerce product dashboard and shopping cart built with **React**, **Vite**, and **Django REST Framework**.

---

## 🚀 Features & Requirements Implemented

- [x] **REST API Integration**: Fetches live product data on initial load from `/api/products/`.
- [x] **Reusable Component Architecture**:
  - `Header`: Navigation, brand badge, live product search with clear button, and cart badge.
  - `CategoryFilter`: Minimalist category pill filters (All, Electronics, Footwear, Fitness, etc.) and sorting options.
  - `ProductCard`: Reusable card displaying product thumbnail, title, formatted price, category tag, star rating, stock indicator, and cart actions.
  - `ProductGrid`: Responsive layout with loading shimmer skeletons, empty state, and error handling.
  - `CartDrawer`: Accessible slide-over drawer showing selected items, line totals, free delivery progress, and total cart amount.
  - `CartItem`: Component for individual cart items with thumbnail, quantity stepper (`+` / `-`), and remove button.
  - `CheckoutModal`: Itemized order summary with mock customer details and order confirmation.
  - `Toast`: Non-intrusive notification feedback on adding, updating, or removing items.
- [x] **Product Display Details**:
  - Product Name (`title`)
  - Price formatted in currency (`₹price`)
  - Category tag
  - Rating (`rating` out of 5.0 with star icon)
  - Product Image (`thumbnail` with broken image fallback)
- [x] **Shopping Cart Capabilities**:
  - Add to Cart (with stock cap protection)
  - Remove from Cart (decrement quantity or remove item)
  - Cart item counter badge in header
  - Line total calculation per product
  - Real-time **Total Cart Amount** calculation (Subtotal + Free delivery threshold calculation)
  - LocalStorage persistence so the cart is preserved on refresh
- [x] **Clean, Minimal Styling**:
  - Pure CSS design system using CSS variables
  - High-contrast typography (`Plus Jakarta Sans` / `Inter`)
  - Modern micro-transitions and accessible interactive states
- [x] **Isolated Virtual Environment (`venv`)**:
  - Backend dependencies installed in a dedicated Python `venv`

---

## 📁 Project Structure

```text
Day_9/
├── backend/
│   ├── core/                  # Django project settings and URLs
│   │   ├── settings.py        # Configured CORS & template paths
│   │   └── urls.py            # API routing & frontend serving
│   ├── products/              # Django App
│   │   ├── models.py          # Product model (title, price, category, rating, stock, thumbnail)
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # ProductListCreate, CategoryList, Availability APIs
│   │   └── management/        # Seeding command (seed_products.py)
│   ├── db.sqlite3             # Seeded SQLite database
│   └── manage.py
├── frontend/                  # React + Vite application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── CategoryFilter.jsx
│   │   │   ├── ProductCard.jsx
│   │   │   ├── ProductGrid.jsx
│   │   │   ├── CartDrawer.jsx
│   │   │   ├── CartItem.jsx
│   │   │   ├── CheckoutModal.jsx
│   │   │   └── Toast.jsx
│   │   ├── services/
│   │   │   └── api.js         # API client with fallback catalog
│   │   ├── App.jsx            # Main dashboard controller
│   │   ├── index.css          # Minimal design tokens & styles
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js         # Vite proxy to backend API
├── requirements.txt           # Python dependencies (Django, DRF, CORS)
├── run.sh                     # Quick start runner script
└── venv/                      # Python virtual environment
```

---

## 🛠️ Quick Start Guide

### Option 1: Automatic Runner (Recommended)

From the `Day_9` directory, run:

```bash
chmod +x run.sh
./run.sh
```

This will automatically:
1. Activate or create the Python `venv`
2. Install Python dependencies
3. Run database migrations & seed initial products
4. Start both the Django API server (`http://127.0.0.1:8000`) and the Vite React server (`http://localhost:5173`)

---

### Option 2: Manual Step-by-Step

#### 1. Backend (Django with `venv`)

```bash
cd /home/muhammedmirzapn/10-day-improvement-plan/Day_9

# Activate the virtual environment
source venv/bin/activate

# Apply migrations and seed sample products
python backend/manage.py migrate
python backend/manage.py seed_products

# Start Django server
python backend/manage.py runserver 127.0.0.1:8000
```

#### 2. Frontend (React with Vite)

In a separate terminal:

```bash
cd /home/muhammedmirzapn/10-day-improvement-plan/Day_9/frontend

# Install dependencies (already pre-installed)
npm install

# Start Vite dev server with HMR
npm run dev
```

Visit **`http://localhost:5173`** in your browser.

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/products/` | List all products (supports `?category=...`, `?search=...`, `?ordering=...`) |
| `POST` | `/api/products/` | Create a new product |
| `GET` | `/api/products/<id>/` | Retrieve single product details |
| `GET` | `/api/categories/` | List all distinct categories |
| `GET` | `/api/products/<id>/availability/` | Check live stock availability |
