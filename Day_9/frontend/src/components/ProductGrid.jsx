import React from 'react';
import ProductCard from './ProductCard';
import { PackageOpen, RotateCcw } from 'lucide-react';

export default function ProductGrid({
  products,
  loading,
  cartItems,
  onAddToCart,
  onRemoveFromCart,
  onResetFilters,
  onRetry,
  error,
}) {
  if (loading) {
    return (
      <div className="product-grid" aria-busy="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton-shimmer skeleton-img" />
            <div className="skeleton-body">
              <div className="skeleton-shimmer skeleton-line" style={{ width: '40%' }} />
              <div className="skeleton-shimmer skeleton-line" style={{ width: '90%' }} />
              <div className="skeleton-shimmer skeleton-line" style={{ width: '65%' }} />
              <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="skeleton-shimmer skeleton-line" style={{ width: '30%', height: 20 }} />
                <div className="skeleton-shimmer skeleton-line" style={{ width: '35%', height: 32 }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-cart-state" style={{ minHeight: '350px' }}>
        <div className="empty-icon-circle">
          <RotateCcw size={32} />
        </div>
        <h3>Failed to Load Products</h3>
        <p>{error}</p>
        <button className="continue-shopping-btn" onClick={onRetry}>
          Try Again
        </button>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="empty-cart-state" style={{ minHeight: '350px' }}>
        <div className="empty-icon-circle">
          <PackageOpen size={32} />
        </div>
        <h3>No Products Found</h3>
        <p>Try adjusting your search terms or selecting a different category filter.</p>
        {onResetFilters && (
          <button className="continue-shopping-btn" onClick={onResetFilters}>
            Reset Filters
          </button>
        )}
      </div>
    );
  }

  // Create a fast lookup map for item quantities in cart
  const cartQtyMap = new Map();
  cartItems.forEach((item) => {
    cartQtyMap.set(item.id, item.quantity);
  });

  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          cartQuantity={cartQtyMap.get(product.id) || 0}
          onAddToCart={onAddToCart}
          onRemoveFromCart={onRemoveFromCart}
        />
      ))}
    </div>
  );
}
