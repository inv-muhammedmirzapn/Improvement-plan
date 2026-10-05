# Day 8: Product Management Dashboard & Django REST API

A modern, responsive Product Management Dashboard demonstrating core **JavaScript ES6+ fundamentals**, **DOM manipulation**, **Browser Storage (localStorage, sessionStorage, Cookies)**, **Promise handling (`.then()` and `async/await`)**, and a **Django REST API backend**.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ installed
- Web browser (Chrome, Firefox, Edge, Safari)

### 2. Start the Django API Backend
Open your terminal and navigate to `Day_8/`:

```bash
cd /home/muhammedmirzapn/10-day-improvement-plan/Day_8

# Activate virtual environment
source venv/bin/activate

# Navigate to backend directory
cd backend

# Run migrations (already prepared)
python manage.py migrate

# Seed database with sample products (if not already seeded)
python manage.py seed_products

# Start Django development server
python manage.py runserver 127.0.0.1:8000
```

The Django API will be live at:
- **API Endpoint:** `http://127.0.0.1:8000/api/products/`
- **Single Product:** `http://127.0.0.1:8000/api/products/1/`
- **Availability Check:** `http://127.0.0.1:8000/api/products/1/availability/`
- **Dashboard Web UI:** `http://127.0.0.1:8000/` (served directly by Django)

### 3. Open the Frontend Dashboard
You have two flexible options:
- **Option A (Via Django Server):** Open `http://127.0.0.1:8000/` in your browser.
- **Option B (Direct Static File / Live Server):** Open `Day_8/frontend/index.html` directly in your browser or with VS Code Live Server. The frontend connects to the Django API at `http://127.0.0.1:8000/api/products/` via `fetch()`.

---

## 📂 Project Architecture

```
Day_8/
├── backend/                             # Django REST API Project
│   ├── core/                            # Project Settings & URLs
│   │   ├── settings.py                  # CORS, DRF, Apps & Templates config
│   │   ├── urls.py                      # Route mappings for API & UI
│   │   └── wsgi.py
│   ├── products/                        # Products Django Application
│   │   ├── models.py                    # Product Model (id, title, price, category, etc.)
│   │   ├── serializers.py              # DRF ModelSerializer
│   │   ├── views.py                     # List/Create, Detail, Availability views
│   │   ├── urls.py                      # API URL routing
│   │   └── management/commands/
│   │       └── seed_products.py         # 18 Realistic seed catalog items
│   ├── db.sqlite3                       # SQLite database
│   └── manage.py
├── frontend/                            # Pure HTML/CSS/JS Client
│   ├── index.html                       # Semantic HTML5 Structure & ARIA attributes
│   ├── style.css                        # Modern Dark Glassmorphic Design System
│   └── app.js                           # Core ES6 Logic (fetch, filter, map, reduce, storage)
├── venv/                                # Python Virtual Environment
├── requirements.txt                     # Django, DRF, django-cors-headers
└── README.md                            # Documentation & Concepts Guide
```

---

## 🎯 Implementation of Required Concepts

| Requirement | Implementation in Code |
| :--- | :--- |
| **`fetch()` + `async/await`** | `fetchProducts()` in `app.js` queries `GET /api/products/` with asynchronous JSON parsing. |
| **Search by name using `filter()`** | `rawProducts.filter(p => p.title.toLowerCase().includes(currentSearch))` |
| **Category filter using `filter()`** | `products.filter(p => p.category.toLowerCase() === currentCategory)` |
| **Sorting with spread operator** | `[...filtered].sort((a, b) => ...)` supports Name, Price (Asc/Desc), and Rating. |
| **Average price using `reduce()`** | `catalog.reduce((acc, p) => acc + Number(p.price), 0) / count` |
| **Highest priced product** | `catalog.reduce((max, p) => p.price > max.price ? p : max, catalog[0])` |
| **Products in stock count** | Filtered by `p.stock > 0`, plus total units summed with `reduce()`. |
| **Transform/Display using `map()`** | Product card HTML generated via `productsToRender.map(product => ...).join('')`. |
| **Destructuring properties** | `const { id, title, price, category, rating, stock, thumbnail } = product;` |
| **Spread operator usage** | `[...filtered]`, `[...favoriteIds, productId]`, `[productId, ...filtered]`. |
| **Favorites in `localStorage`** | ⭐ Toggle stores IDs in `localStorage['omnistock_favorite_ids']`, with "Show Favorites" filter. |
| **Preferred Category in `Cookie`** | Saved in `document.cookie` (`omnistock_preferred_category`), restored automatically upon reopening. |
| **Promise: `checkProductAvailability`** | Returns a custom `new Promise((resolve, reject) => { ... })` with simulated processing. |
| **`.then()` Promise Handling** | "⚡ Quick Check" button invokes `checkProductAvailability(id).then(...).catch(...)`. |
| **`async/await` Promise Handling** | "View Details" modal executes `await checkProductAvailability(id)` with `try/catch`. |
| **Recently Viewed Products** | Recorded in `sessionStorage['omnistock_recently_viewed']`, displayed in recent carousel. |

---

## 📚 HTTP & Browser Concepts Guide

### 1. What happens when the frontend sends an HTTP GET request?
When the frontend invokes `fetch('http://127.0.0.1:8000/api/products/')`, the following sequence occurs:
1. **URL Parsing & DNS Resolution**: The browser parses the protocol (`http`), host (`127.0.0.1`), port (`8000`), and path (`/api/products/`). If a domain name was used (e.g., `api.example.com`), DNS resolves the domain to an IP address.
2. **TCP Handshake & TLS**: The browser establishes a Transmission Control Protocol (TCP) connection (SYN, SYN-ACK, ACK). If HTTPS is used, a TLS handshake encrypts the connection.
3. **HTTP Request Generation**: The browser formats and sends an HTTP Request message consisting of:
   - **Request Line:** `GET /api/products/ HTTP/1.1`
   - **Headers:** `Host: 127.0.0.1:8000`, `Accept: application/json`, `User-Agent: ...`
   - **Body:** None for standard GET requests.
4. **Server Processing**: The Django web server parses the request, matches the URL in `core/urls.py`, calls `ProductListCreateAPIView`, queries the SQLite database (`Product.objects.all()`), serializes the records to JSON, and prepares the HTTP response.
5. **HTTP Response Transmission**: Django sends back status `200 OK`, headers (including `Content-Type: application/json` and CORS headers), and the JSON byte payload.
6. **Browser Processing**: The JavaScript `fetch()` Promise resolves with a `Response` object. `await response.json()` parses the JSON text into JavaScript objects.

---

### 2. Difference Between Request and Response

| Feature | HTTP Request | HTTP Response |
| :--- | :--- | :--- |
| **Originator** | Initiated by the Client (Frontend / Browser). | Generated and sent by the Server (Django). |
| **Purpose** | Asks for a resource (`GET`) or submits data (`POST`, `PUT`, `DELETE`). | Delivers the requested data or reports the outcome of the action. |
| **Key Components** | HTTP Method, URI path, Query Parameters, Request Headers, Request Body. | HTTP Status Code, Status Message, Response Headers, Response Body. |
| **Example** | `GET /api/products/ HTTP/1.1` | `HTTP/1.1 200 OK` + `[{"id": 1, ...}]` |

---

### 3. Common HTTP Status Codes

- **`200 OK`**: The request succeeded. The server processed the request and returned the requested data (e.g., successfully returning product list).
- **`400 Bad Request`**: The client sent a request with invalid syntax, missing required fields, or malformed data that the server cannot understand.
- **`401 Unauthorized`**: Authentication is required and has failed or has not been provided. The user must log in or supply a valid API key/JWT.
- **`404 Not Found`**: The requested resource URI does not exist on the server (e.g., requesting `/api/products/9999/` for a non-existent product).
- **`500 Internal Server Error`**: An unhandled exception or bug occurred on the server while trying to fulfill the request (e.g., database connection crash).

---

### 4. What CORS is and Why Browsers Enforce It
**CORS (Cross-Origin Resource Sharing)** is a browser security mechanism based on the **Same-Origin Policy (SOP)**. 
- An **Origin** is defined by the combination of **Protocol + Domain + Port** (e.g., `http://localhost:3000` vs `http://127.0.0.1:8000`).
- By default, browsers block frontend JavaScript from reading responses returned by a different origin to prevent malicious websites from stealing sensitive data or session tokens from another service.
- When an API wants to allow cross-origin requests, it must include HTTP headers such as:
  ```http
  Access-Control-Allow-Origin: *
  Access-Control-Allow-Methods: GET, POST, OPTIONS
  Access-Control-Allow-Headers: Content-Type, Authorization
  ```
- In our Django backend, `django-cors-headers` automatically injects these headers via `corsheaders.middleware.CorsMiddleware`.

---

### 5. Difference Between localStorage, sessionStorage, and Cookies

| Property | `localStorage` | `sessionStorage` | `Cookies` (`document.cookie`) |
| :--- | :--- | :--- | :--- |
| **Persistence / Lifetime** | Persistent across browser sessions until explicitly cleared. | Cleared automatically when the browser tab or window is closed. | Configurable via `expires` or `max-age`; can persist or act as session cookies. |
| **Storage Capacity** | ~5 MB to 10 MB per origin. | ~5 MB per origin. | ~4 KB per cookie (limited). |
| **Server Transmission** | Never transmitted over HTTP requests automatically; client-side only. | Never transmitted over HTTP requests automatically; client-side only. | Sent to the server automatically with every matching HTTP request header (`Cookie:`). |
| **Accessibility** | Any window/tab of the same origin. | Only the specific tab that opened it. | Accessible to both client scripts (unless `HttpOnly`) and server. |
| **Dashboard Usage** | **Favorite Product IDs (`⭐`)** — retained after refresh/restart. | **Recently Viewed Products (`🕒`)** — active during user browsing session. | **Preferred Category (`🍪`)** — persists user default category preference. |

---

### 6. What Happens When an API Request Fails?
When an API request fails (e.g., server offline, network timeout, or 4xx/5xx HTTP error):
1. **Network Layer Failure**: If DNS fails, the server is unreachable, or CORS is rejected, the browser throws a `TypeError: Failed to fetch`. The Promise rejects immediately.
2. **HTTP Error Status (e.g. 404 or 500)**: The `fetch()` Promise actually *resolves* (not rejects), but `response.ok` is set to `false`.
3. **Application Handling**:
   - The application checks `if (!response.ok) throw new Error(...)`.
   - The `catch (error)` block intercepts the failure.
   - User feedback is provided via UI status badges and toast error notifications.

---

### 7. How to Inspect the API in Browser DevTools → Network Tab

To inspect the live API request and response:
1. Open the application in Google Chrome, Edge, or Firefox.
2. Press <kbd>F12</kbd> (or right-click anywhere on the page and select **Inspect**).
3. Switch to the **Network** tab in DevTools.
4. Select the **Fetch/XHR** filter pill at the top of the Network panel.
5. In the OmniStock dashboard, click the **"Sync API"** button or refresh the page.
6. Look for the `products/` request in the list:
   - **Headers Tab**: Review the Request URL, Request Method (`GET`), Status Code (`200 OK`), Request Headers, and Response Headers (`access-control-allow-origin`).
   - **Response Tab**: Inspect the raw JSON array returned by Django.
   - **Preview Tab**: Expand and inspect individual product objects.
   - **Timing Tab**: View DNS resolution, connection setup, and Time To First Byte (TTFB).

---

## 🧪 Testing Checklist

- [x] **API Connectivity**: Django server returns JSON from `GET /api/products/`.
- [x] **Fetch & Async/Await**: Products fetched strictly from the Django API.
- [x] **Search**: Typing into search bar filters products by title using `filter()`.
- [x] **Category Filter**: Selecting a category isolates matching products using `filter()`.
- [x] **Sorting**: All 4 sort options (A→Z, Price Low/High, Rating) create new arrays via `[...spread]`.
- [x] **Statistics**: Total count, average price via `reduce()`, highest product, and in-stock units update dynamically.
- [x] **Favorites**: Clicking ⭐ adds/removes product IDs in `localStorage`; "Show Favorites" filter works.
- [x] **Cookies**: Clicking "Save as Preferred" stores category in cookie; reloading page restores the filter.
- [x] **Promise Handling (.then)**: "Quick Check" button executes `checkProductAvailability().then().catch()`.
- [x] **Promise Handling (async/await)**: "View Details" opens modal executing `await checkProductAvailability()`.
- [x] **Recently Viewed**: Products inspected are recorded in `sessionStorage` and visible in Recent section.
- [x] **Aesthetics**: Responsive dark glassmorphic UI with vibrant accents, micro-animations, and clean typography.
