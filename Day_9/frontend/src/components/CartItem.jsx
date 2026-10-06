import React, { useState } from 'react';
import { Plus, Minus, Trash2, ImageOff } from 'lucide-react';

export default function CartItem({
  item,
  onIncrement,
  onDecrement,
  onRemove,
}) {
  const [imgError, setImgError] = useState(false);
  const lineTotal = Number(item.price) * item.quantity;
  const isMaxStock = item.stock && item.quantity >= item.stock;

  return (
    <div className="cart-item">
      {imgError || !item.thumbnail ? (
        <div className="cart-item-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ImageOff size={22} color="#94a3b8" />
        </div>
      ) : (
        <img
          src={item.thumbnail}
          alt={item.title}
          className="cart-item-thumb"
          onError={() => setImgError(true)}
        />
      )}

      <div className="cart-item-info">
        <h4 className="cart-item-title" title={item.title}>
          {item.title}
        </h4>
        <div className="cart-item-category">{item.category}</div>
        <div className="cart-item-price-unit">
          ₹{Number(item.price).toLocaleString()} each
        </div>

        <div className="cart-item-actions">
          <div className="cart-item-stepper">
            <button
              type="button"
              onClick={() => onDecrement(item.id)}
              title="Decrease quantity"
              aria-label={`Decrease quantity of ${item.title}`}
            >
              <Minus size={13} />
            </button>
            <span aria-live="polite">{item.quantity}</span>
            <button
              type="button"
              onClick={() => onIncrement(item)}
              disabled={isMaxStock}
              title={isMaxStock ? "Maximum available stock reached" : "Increase quantity"}
              aria-label={`Increase quantity of ${item.title}`}
              style={{ opacity: isMaxStock ? 0.35 : 1 }}
            >
              <Plus size={13} />
            </button>
          </div>

          <button
            type="button"
            className="cart-item-remove-btn"
            onClick={() => onRemove(item.id)}
            title="Remove item from cart"
            aria-label={`Remove ${item.title} from cart`}
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="cart-item-total">
        ₹{lineTotal.toLocaleString()}
      </div>
    </div>
  );
}
