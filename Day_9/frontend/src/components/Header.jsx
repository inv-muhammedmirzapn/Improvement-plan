import React from 'react';
import { ShoppingBag, Search, X, ShoppingCart } from 'lucide-react';

export default function Header({
  searchQuery,
  setSearchQuery,
  cartCount,
  cartTotal,
  onOpenCart,
  dataSource,
}) {
  return (
    <header className="site-header">
      <div className="header-inner">
        {/* Brand */}
        <div className="brand-section">
          <div className="brand-icon">
            <ShoppingBag size={20} strokeWidth={2.2} />
          </div>
          <div>
            <h1 className="brand-title">ShopDash</h1>
            <p className="brand-subtitle">Product Catalog & Cart</p>
          </div>
        </div>

        {/* Search */}
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            className="search-input"
            placeholder="Search products by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              className="search-clear-btn"
              onClick={() => setSearchQuery('')}
              title="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Cart Trigger */}
        <div className="header-actions">
          <button
            className="cart-button-trigger"
            onClick={onOpenCart}
            aria-label="View Shopping Cart"
          >
            <ShoppingCart size={18} />
            <span>Cart</span>
            {cartCount > 0 && (
              <span className="cart-count-badge">{cartCount}</span>
            )}
            {cartTotal > 0 && (
              <span style={{ fontSize: '0.82rem', opacity: 0.9 }}>
                ₹{cartTotal.toLocaleString()}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
