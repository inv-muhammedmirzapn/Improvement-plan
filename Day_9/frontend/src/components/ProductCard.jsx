import React, { useState } from 'react';
import { Star, Plus, Minus, ShoppingCart, ImageOff } from 'lucide-react';

export default function ProductCard({
  product,
  cartQuantity = 0,
  onAddToCart,
  onRemoveFromCart,
}) {
  const [imgError, setImgError] = useState(false);
  const isOutOfStock = product.stock === 0;

  return (
    <article className="product-card" aria-label={product.title}>
      {/* Image Container */}
      <div className="product-card-image-wrapper">
        <span className="product-category-tag">{product.category}</span>
        
        <span
          className={`stock-tag ${isOutOfStock ? 'out-stock' : 'in-stock'}`}
        >
          {isOutOfStock ? 'Out of stock' : `${product.stock} in stock`}
        </span>

        {imgError || !product.thumbnail ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#94a3b8' }}>
            <ImageOff size={32} />
            <span style={{ fontSize: '0.75rem', marginTop: 4 }}>No Image</span>
          </div>
        ) : (
          <img
            src={product.thumbnail}
            alt={product.title}
            className="product-card-image"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        )}
      </div>

      {/* Card Body */}
      <div className="product-card-body">
        {/* Rating */}
        <div className="product-rating">
          <Star size={14} className="rating-star-icon" />
          <span className="rating-score">{Number(product.rating).toFixed(1)}</span>
          <span>/ 5.0</span>
        </div>

        {/* Product Title */}
        <h2 className="product-title" title={product.title}>
          {product.title}
        </h2>

        {/* Card Footer: Price & Cart Actions */}
        <div className="product-card-footer">
          <div className="product-price">
            <span className="price-label">Price</span>
            <span className="price-value">₹{Number(product.price).toLocaleString()}</span>
          </div>

          {cartQuantity > 0 ? (
            <div className="card-quantity-controls">
              <button
                type="button"
                className="card-qty-btn"
                onClick={() => onRemoveFromCart(product.id)}
                title="Decrease quantity"
                aria-label={`Decrease ${product.title} in cart`}
              >
                <Minus size={14} />
              </button>
              <span className="card-qty-count" aria-live="polite">
                {cartQuantity}
              </span>
              <button
                type="button"
                className="card-qty-btn"
                onClick={() => onAddToCart(product)}
                disabled={cartQuantity >= product.stock}
                title={cartQuantity >= product.stock ? "Max stock reached" : "Increase quantity"}
                aria-label={`Increase ${product.title} in cart`}
                style={{ opacity: cartQuantity >= product.stock ? 0.4 : 1 }}
              >
                <Plus size={14} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="add-cart-btn"
              onClick={() => onAddToCart(product)}
              disabled={isOutOfStock}
              title={isOutOfStock ? "Product is out of stock" : "Add to Cart"}
            >
              <ShoppingCart size={15} />
              <span>{isOutOfStock ? 'Sold Out' : 'Add to Cart'}</span>
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
