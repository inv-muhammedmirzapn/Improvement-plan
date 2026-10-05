/**
 * Product Management Dashboard
 * Demonstrates:
 * - fetch() and async/await
 * - Array methods: filter(), map(), reduce()
 * - Destructuring and Spread Operator
 * - localStorage (Favorites) & sessionStorage (Recently Viewed)
 * - Cookies (Preferred Category)
 * - Promise handling with .then() and async/await
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api';
const COOKIE_PREF_CAT = 'preferred_category';
const STORAGE_FAVS = 'favorite_products';
const STORAGE_RECENT = 'recently_viewed_products';

// Application State
let products = [];
let favorites = [];
let recentlyViewed = [];
let searchTerm = '';
let selectedCategory = 'All';
let selectedSort = 'name-asc';
let showOnlyFavorites = false;

// DOM Elements
const productsGrid = document.getElementById('products-grid');
const loadingState = document.getElementById('loading-state');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const categorySelect = document.getElementById('category-select');
const sortSelect = document.getElementById('sort-select');
const showFavoritesCheckbox = document.getElementById('show-favorites-checkbox');
const productDetailsSection = document.getElementById('product-details-section');
const productDetailsContent = document.getElementById('product-details-content');
const recentlyViewedList = document.getElementById('recently-viewed-list');

// Stats Elements
const statTotalCount = document.getElementById('stat-total-count');
const statAvgPrice = document.getElementById('stat-avg-price');
const statHighestProduct = document.getElementById('stat-highest-product');
const statInStockCount = document.getElementById('stat-in-stock-count');


// ============================================================================
// Cookie Management Helper Functions
// ============================================================================

function setCookie(name, value, days = 7) {
  const date = new Date();
  date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)};expires=${date.toUTCString()};path=/;SameSite=Lax`;
}

function getCookie(name) {
  const key = encodeURIComponent(name) + "=";
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    let c = cookie.trim();
    if (c.indexOf(key) === 0) {
      return decodeURIComponent(c.substring(key.length));
    }
  }
  return null;
}

function deleteCookie(name) {
  document.cookie = `${encodeURIComponent(name)}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;SameSite=Lax`;
}


// ============================================================================
// Promise Handling: checkProductAvailability
// ============================================================================

/**
 * Promise-based function to simulate checking product availability.
 */
function checkProductAvailability(productId) {
  return new Promise((resolve, reject) => {
    // Simulate API processing delay (600ms)
    setTimeout(() => {
      const numericId = Number(productId);
      const product = products.find(p => p.id === numericId);

      if (!product) {
        reject(new Error(`Product ID #${productId} not found.`));
        return;
      }

      // Destructuring product properties
      const { id, title, stock } = product;

      if (stock > 0) {
        resolve({
          productId: id,
          title,
          available: true,
          stock,
          message: `In Stock: ${stock} units available.`
        });
      } else {
        resolve({
          productId: id,
          title,
          available: false,
          stock: 0,
          message: `Out of Stock: 0 units available.`
        });
      }
    }, 600);
  });
}


// ============================================================================
// Fetch Product Data (fetch and async/await)
// ============================================================================

async function fetchProducts() {
  loadingState.style.display = 'block';
  productsGrid.innerHTML = '';
  emptyState.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE_URL}/products/`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    products = data;

    // Populate category dropdowns
    populateCategories();

    // Restore preferred category from Cookie
    restorePreferredCategoryCookie();

    // Render products & statistics
    render();
  } catch (error) {
    console.error('Error fetching products:', error);
    loadingState.textContent = `Failed to load products: ${error.message}. Ensure Django backend is running.`;
  } finally {
    if (products.length > 0) {
      loadingState.style.display = 'none';
    }
  }
}


// ============================================================================
// Categories and Cookie Restore
// ============================================================================

function populateCategories() {
  // Use map() and Set to get distinct categories
  const categories = [...new Set(products.map(p => p.category))];

  // Category filter dropdown
  categorySelect.innerHTML = '<option value="All">All Categories</option>' +
    categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
}

function restorePreferredCategoryCookie() {
  const preferred = getCookie(COOKIE_PREF_CAT);
  if (preferred) {
    selectedCategory = preferred;
    categorySelect.value = preferred;
  }
}


// ============================================================================
// Statistics (using reduce and destructuring)
// ============================================================================

function updateStatistics(catalog) {
  // 1. Total number of products
  statTotalCount.textContent = catalog.length;

  if (catalog.length === 0) {
    statAvgPrice.textContent = '₹0.00';
    statHighestProduct.textContent = '-';
    statInStockCount.textContent = '0';
    return;
  }

  // 2. Average product price using reduce()
  const totalPrice = catalog.reduce((sum, product) => {
    const { price } = product; // destructuring
    return sum + Number(price);
  }, 0);
  const avg = (totalPrice / catalog.length).toFixed(2);
  statAvgPrice.textContent = `₹${avg}`;

  // 3. Highest-priced product using reduce() and destructuring
  const highest = catalog.reduce((max, product) => {
    return Number(product.price) > Number(max.price) ? product : max;
  }, catalog[0]);

  const { title: maxTitle, price: maxPrice } = highest; // destructuring
  statHighestProduct.textContent = `${maxTitle} (₹${maxPrice})`;

  // 4. Number of products currently in stock using filter()
  const inStock = catalog.filter(product => {
    const { stock } = product; // destructuring
    return stock > 0;
  });
  statInStockCount.textContent = inStock.length;
}


// ============================================================================
// Render Products (using map, filter, destructuring, and spread operator)
// ============================================================================

function render() {
  // 1. Filter by search name using filter()
  let filtered = products.filter(product => {
    const { title } = product; // destructuring
    return title.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // 2. Filter by category using filter()
  if (selectedCategory && selectedCategory !== 'All') {
    filtered = filtered.filter(product => {
      const { category } = product; // destructuring
      return category.toLowerCase() === selectedCategory.toLowerCase();
    });
  }

  // 3. Filter by favorites if toggled
  if (showOnlyFavorites) {
    filtered = filtered.filter(product => {
      const { id } = product; // destructuring
      return favorites.includes(id);
    });
  }

  // 4. Sorting using spread operator [...filtered]
  const sorted = [...filtered].sort((a, b) => {
    const { title: titleA, price: priceA, rating: ratingA } = a; // destructuring
    const { title: titleB, price: priceB, rating: ratingB } = b; // destructuring

    switch (selectedSort) {
      case 'name-asc':
        return titleA.localeCompare(titleB);
      case 'price-asc':
        return priceA - priceB;
      case 'price-desc':
        return priceB - priceA;
      case 'rating-desc':
        return ratingB - ratingA;
      default:
        return 0;
    }
  });

  // Update statistics
  updateStatistics(products);

  // Render cards using map() and destructuring
  if (sorted.length === 0) {
    productsGrid.innerHTML = '';
    emptyState.style.display = 'block';
  } else {
    emptyState.style.display = 'none';
    productsGrid.innerHTML = sorted.map(product => {
      // Destructuring product properties
      const { id, title, price, category, rating, stock, thumbnail } = product;
      const isFav = favorites.includes(id);

      return `
        <article class="product-card">
          <div class="product-img-wrapper">
            <img src="${thumbnail}" alt="${title}" class="product-img" onerror="this.src='https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&auto=format&fit=crop&q=80'">
            <span class="product-category">${category}</span>
            <button class="fav-btn ${isFav ? 'is-fav' : ''}" onclick="toggleFavorite(${id})" title="Mark Favorite">
              ${isFav ? '⭐' : '☆'}
            </button>
          </div>

          <h3 class="product-name">${title}</h3>
          <div class="product-price">₹${price}</div>

          <div class="product-meta">
            <span>Rating: ★ ${rating}</span>
            <span>Stock: ${stock}</span>
          </div>

          <div class="product-actions">
            <!-- Handled with .then() -->
            <button onclick="handleQuickCheckWithThen(${id}, this)">Check</button>

            <!-- Handled with async/await -->
            <button onclick="handleViewDetailsWithAsync(${id})">Details</button>
          </div>

          <div id="availability-msg-${id}" class="card-availability-msg" style="display: none;"></div>
        </article>
      `;
    }).join('');
  }

  // Update Recently Viewed List
  renderRecentlyViewed();
}


// ============================================================================
// Promise Handling Implementation:
// Place 1: Using .then() for inline availability check
// ============================================================================

function handleQuickCheckWithThen(productId, buttonElement) {
  const msgEl = document.getElementById(`availability-msg-${productId}`);
  msgEl.style.display = 'block';
  msgEl.textContent = 'Checking availability...';

  // Handling Promise using .then() and .catch()
  checkProductAvailability(productId)
    .then(result => {
      const { message, available } = result; // destructuring
      msgEl.textContent = message;
      msgEl.style.color = available ? '#2e7d32' : '#c62828';
    })
    .catch(error => {
      msgEl.textContent = `Error: ${error.message}`;
      msgEl.style.color = '#c62828';
    });
}


// ============================================================================
// Promise Handling Implementation:
// Place 2: Using async/await when viewing product details
// ============================================================================

async function handleViewDetailsWithAsync(productId) {
  const numericId = Number(productId);
  const product = products.find(p => p.id === numericId);
  if (!product) return;

  // Add to Recently Viewed Products in sessionStorage
  recordRecentlyViewed(numericId);

  // Destructuring product properties
  const { id, title, price, category, rating, stock, thumbnail } = product;

  productDetailsSection.style.display = 'block';
  productDetailsContent.innerHTML = `
    <div class="details-content">
      <img src="${thumbnail}" alt="${title}" class="details-thumb">
      <div class="details-info">
        <h3>${title}</h3>
        <p><strong>Price:</strong> ₹${price}</p>
        <p><strong>Category:</strong> ${category}</p>
        <p><strong>Rating:</strong> ★ ${rating}</p>
        <p><strong>Catalog Stock:</strong> ${stock} units</p>
        <div id="details-availability-box" class="details-availability">
          Checking availability via async/await...
        </div>
      </div>
    </div>
  `;

  // Scroll to details
  productDetailsSection.scrollIntoView({ behavior: 'smooth' });

  // Handling Promise using async/await and try/catch
  try {
    const result = await checkProductAvailability(numericId);
    const { message, available } = result; // destructuring

    const box = document.getElementById('details-availability-box');
    if (box) {
      box.textContent = message;
      box.style.background = available ? '#e8f5e9' : '#ffebee';
      box.style.borderColor = available ? '#c8e6c9' : '#ffcdd2';
      box.style.color = available ? '#2e7d32' : '#c62828';
    }
  } catch (error) {
    const box = document.getElementById('details-availability-box');
    if (box) {
      box.textContent = `Error checking availability: ${error.message}`;
      box.style.color = '#c62828';
    }
  }
}


// ============================================================================
// Favorites (localStorage and spread operator)
// ============================================================================

function loadFavorites() {
  try {
    const saved = localStorage.getItem(STORAGE_FAVS);
    favorites = saved ? JSON.parse(saved) : [];
  } catch (e) {
    favorites = [];
  }
}

function toggleFavorite(productId) {
  const isFav = favorites.includes(productId);

  if (isFav) {
    // Remove using filter()
    favorites = favorites.filter(id => id !== productId);
  } else {
    // Add using spread operator: [...favorites, productId]
    favorites = [...favorites, productId];
  }

  // Persist in localStorage
  localStorage.setItem(STORAGE_FAVS, JSON.stringify(favorites));

  render();
}


// ============================================================================
// Recently Viewed Products (sessionStorage and spread operator)
// ============================================================================

function loadRecentlyViewed() {
  try {
    const saved = sessionStorage.getItem(STORAGE_RECENT);
    recentlyViewed = saved ? JSON.parse(saved) : [];
  } catch (e) {
    recentlyViewed = [];
  }
}

function recordRecentlyViewed(productId) {
  // Using spread operator to update array
  const remaining = recentlyViewed.filter(id => id !== productId);
  recentlyViewed = [productId, ...remaining].slice(0, 6);

  sessionStorage.setItem(STORAGE_RECENT, JSON.stringify(recentlyViewed));
  renderRecentlyViewed();
}

function renderRecentlyViewed() {
  if (recentlyViewed.length === 0) {
    recentlyViewedList.innerHTML = '<p style="color:#888; font-size:0.85rem;">No recently viewed products yet. Click "Details" on any product.</p>';
    return;
  }

  // Map recently viewed IDs to product objects and render with map()
  const recentItems = recentlyViewed
    .map(id => products.find(p => p.id === id))
    .filter(Boolean);

  recentlyViewedList.innerHTML = recentItems.map(item => {
    const { id, title, price, thumbnail } = item; // destructuring
    return `
      <div class="recent-card" onclick="handleViewDetailsWithAsync(${id})">
        <img src="${thumbnail}" alt="${title}" onerror="this.src='https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&auto=format&fit=crop&q=80'">
        <div class="recent-title">${title}</div>
        <div class="recent-price">₹${price}</div>
      </div>
    `;
  }).join('');
}


// ============================================================================
// Event Listeners
// ============================================================================

// Search by name using filter()
searchInput.addEventListener('input', (e) => {
  searchTerm = e.target.value;
  render();
});

// Category filter using filter() and preferred category cookie
categorySelect.addEventListener('change', (e) => {
  selectedCategory = e.target.value;
  if (selectedCategory && selectedCategory !== 'All') {
    setCookie(COOKIE_PREF_CAT, selectedCategory, 7);
  } else {
    deleteCookie(COOKIE_PREF_CAT);
  }
  render();
});

// Sort select with spread operator
sortSelect.addEventListener('change', (e) => {
  selectedSort = e.target.value;
  render();
});

// Show favorites checkbox
showFavoritesCheckbox.addEventListener('change', (e) => {
  showOnlyFavorites = e.target.checked;
  render();
});

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadFavorites();
  loadRecentlyViewed();
  fetchProducts();
});

// Expose handlers to window for inline HTML onclick attributes
window.toggleFavorite = toggleFavorite;
window.handleQuickCheckWithThen = handleQuickCheckWithThen;
window.handleViewDetailsWithAsync = handleViewDetailsWithAsync;
