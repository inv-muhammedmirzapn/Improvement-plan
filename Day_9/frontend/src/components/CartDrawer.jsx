import React from 'react';
import { X, ShoppingBag, ArrowRight } from 'lucide-react';
import CartItem from './CartItem';

export default function CartDrawer({
  isOpen,
  onClose,
  cartItems,
  onIncrement,
  onDecrement,
  onRemove,
  onClearCart,
  onCheckout,
}) {
  if (!isOpen) return null;

  // Calculate totals
  const totalItemsCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);
  const totalAmount = cartItems.reduce(
    (acc, item) => acc + Number(item.price) * item.quantity,
    0
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="cart-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over Drawer */}
      <aside
        className="cart-drawer"
        role="dialog"
        aria-label="Shopping Cart"
      >
        {/* Header */}
        <div className="cart-drawer-header">
          <div className="cart-drawer-title-group">
            <h3 className="cart-drawer-title">Shopping Cart</h3>
            <span className="cart-drawer-count">
              {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'}
            </span>
          </div>

          <button
            type="button"
            className="close-drawer-btn"
            onClick={onClose}
            title="Close Cart"
            aria-label="Close Shopping Cart"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content Body */}
        {cartItems.length === 0 ? (
          <div className="empty-cart-state">
            <div className="empty-icon-circle">
              <ShoppingBag size={32} />
            </div>
            <h3>Your Cart is Empty</h3>
            <p>Looks like you have not added any products to your cart yet.</p>
            <button
              type="button"
              className="continue-shopping-btn"
              onClick={onClose}
            >
              Browse Products
            </button>
          </div>
        ) : (
          <>
            {/* Items List */}
            <div className="cart-items-list">
              {cartItems.map((item) => (
                <CartItem
                  key={item.id}
                  item={item}
                  onIncrement={onIncrement}
                  onDecrement={onDecrement}
                  onRemove={onRemove}
                />
              ))}
            </div>

            {/* Cart Footer / Summary */}
            <div className="cart-drawer-footer">
              <div className="summary-row">
                <span>Total Items</span>
                <span>{totalItemsCount}</span>
              </div>

              <div className="summary-row total">
                <span>Total Cart Amount</span>
                <span>₹{totalAmount.toLocaleString()}</span>
              </div>

              <button
                type="button"
                className="checkout-btn"
                onClick={onCheckout}
              >
                <span>Proceed to Checkout</span>
                <ArrowRight size={18} />
              </button>

              <button
                type="button"
                className="clear-cart-btn"
                onClick={onClearCart}
              >
                Clear cart
              </button>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
