import React, { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import CategoryFilter from './components/CategoryFilter';
import ProductGrid from './components/ProductGrid';
import CartDrawer from './components/CartDrawer';
import CheckoutModal from './components/CheckoutModal';
import Toast from './components/Toast';
import { fetchProducts, fetchCategories } from './services/api';

const CART_STORAGE_KEY = 'shopdash_cart_v1';

export default function App() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState(['All']);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('default');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState('backend');

  // Cart State (loaded from localStorage)
  const [cartItems, setCartItems] = useState(() => {
    try {
      const saved = localStorage.getItem(CART_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (_) {
      return [];
    }
  });

  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Sync Cart to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cartItems));
    } catch (_) {}
  }, [cartItems]);

  // Toast Helper
  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((current) => (current === msg ? null : current));
    }, 2400);
  };

  // Fetch Categories on Mount
  useEffect(() => {
    async function loadCategories() {
      try {
        const cats = await fetchCategories();
        if (cats && cats.length > 0) {
          setCategories(cats);
        }
      } catch (err) {
        console.error('Failed to load categories', err);
      }
    }
    loadCategories();
  }, []);

  // Fetch Products from REST API
  const loadProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProducts({
        category: selectedCategory,
        search: searchQuery,
      });
      setProducts(res.data);
      setDataSource(res.source);
    } catch (err) {
      setError(err.message || 'Error fetching products from server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, [selectedCategory, searchQuery]);

  // Local Sort of Displayed Products
  const sortedProducts = useMemo(() => {
    const list = [...products];
    if (sortBy === 'price-asc') {
      return list.sort((a, b) => Number(a.price) - Number(b.price));
    }
    if (sortBy === 'price-desc') {
      return list.sort((a, b) => Number(b.price) - Number(a.price));
    }
    if (sortBy === 'rating-desc') {
      return list.sort((a, b) => Number(b.rating) - Number(a.rating));
    }
    if (sortBy === 'title-asc') {
      return list.sort((a, b) => a.title.localeCompare(b.title));
    }
    return list;
  }, [products, sortBy]);

  // Cart Handlers
  const handleAddToCart = (product) => {
    setCartItems((prev) => {
      const existing = prev.find((item) => item.id === product.id);
      if (existing) {
        if (product.stock && existing.quantity >= product.stock) {
          showToast(`Maximum stock reached for "${product.title}"`);
          return prev;
        }
        showToast(`Increased quantity of "${product.title}"`);
        return prev.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      showToast(`Added "${product.title}" to cart`);
      return [...prev, { ...product, quantity: 1 }];
    });
  };

  const handleDecrementFromCart = (productId) => {
    setCartItems((prev) => {
      const existing = prev.find((item) => item.id === productId);
      if (!existing) return prev;
      if (existing.quantity <= 1) {
        showToast(`Removed "${existing.title}" from cart`);
        return prev.filter((item) => item.id !== productId);
      }
      return prev.map((item) =>
        item.id === productId
          ? { ...item, quantity: item.quantity - 1 }
          : item
      );
    });
  };

  const handleRemoveItem = (productId) => {
    setCartItems((prev) => {
      const item = prev.find((i) => i.id === productId);
      if (item) showToast(`Removed "${item.title}" from cart`);
      return prev.filter((i) => i.id !== productId);
    });
  };

  const handleClearCart = () => {
    if (window.confirm('Are you sure you want to clear your shopping cart?')) {
      setCartItems([]);
      showToast('Shopping cart cleared');
    }
  };

  const handleOrderSuccess = () => {
    setCartItems([]);
    setIsCheckoutOpen(false);
    setIsCartOpen(false);
    showToast('🎉 Order placed successfully!');
  };

  // Cart Metrics
  const cartCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);
  const cartTotal = cartItems.reduce(
    (acc, item) => acc + Number(item.price) * item.quantity,
    0
  );

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        cartCount={cartCount}
        cartTotal={cartTotal}
        onOpenCart={() => setIsCartOpen(true)}
        dataSource={dataSource}
      />

      {/* Main Content */}
      <main className="main-content">
        {/* Category & Sorting Controls */}
        <CategoryFilter
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          sortBy={sortBy}
          onSortChange={setSortBy}
          totalResults={sortedProducts.length}
        />

        {/* Product Catalog Grid */}
        <ProductGrid
          products={sortedProducts}
          loading={loading}
          cartItems={cartItems}
          onAddToCart={handleAddToCart}
          onRemoveFromCart={handleDecrementFromCart}
          onResetFilters={() => {
            setSelectedCategory('All');
            setSearchQuery('');
            setSortBy('default');
          }}
          onRetry={loadProducts}
          error={error}
        />
      </main>

      {/* Shopping Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        cartItems={cartItems}
        onIncrement={handleAddToCart}
        onDecrement={handleDecrementFromCart}
        onRemove={handleRemoveItem}
        onClearCart={handleClearCart}
        onCheckout={() => {
          setIsCartOpen(false);
          setIsCheckoutOpen(true);
        }}
      />

      {/* Checkout Modal */}
      <CheckoutModal
        isOpen={isCheckoutOpen}
        onClose={() => setIsCheckoutOpen(false)}
        cartItems={cartItems}
        onOrderSuccess={handleOrderSuccess}
      />

      {/* Toast Notification */}
      <Toast message={toastMessage} />
    </div>
  );
}
