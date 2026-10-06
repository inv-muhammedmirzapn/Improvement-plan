import React, { useState } from 'react';
import { X, CheckCircle, ArrowRight } from 'lucide-react';

export default function CheckoutModal({
  isOpen,
  onClose,
  cartItems,
  onOrderSuccess,
}) {
  const [placed, setPlaced] = useState(false);
  const [formData, setFormData] = useState({
    name: 'Muhammed Mirza',
    email: 'mirza@example.com',
    address: '221B Baker Street, Suite 400',
  });

  if (!isOpen) return null;

  const totalAmount = cartItems.reduce(
    (acc, item) => acc + Number(item.price) * item.quantity,
    0
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    setPlaced(true);
    setTimeout(() => {
      onOrderSuccess();
    }, 1500);
  };

  const handleReset = () => {
    setPlaced(false);
    onClose();
  };

  return (
    <div className="checkout-modal-backdrop" onClick={handleReset}>
      <div
        className="checkout-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <div className="checkout-modal-header">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
            {placed ? 'Order Confirmed' : 'Checkout'}
          </h3>
          <button
            type="button"
            className="close-drawer-btn"
            onClick={handleReset}
          >
            <X size={20} />
          </button>
        </div>

        <div className="checkout-modal-body">
          {placed ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <CheckCircle
                size={48}
                color="#16a34a"
                style={{ margin: '0 auto 12px' }}
              />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: 8 }}>
                Order Placed!
              </h3>
              <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: 16 }}>
                Your order of ₹{totalAmount.toLocaleString()} has been placed successfully.
              </p>
              <button
                type="button"
                className="checkout-btn"
                onClick={handleReset}
              >
                Back to Store
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ backgroundColor: '#f8fafc', padding: '12px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                  <span style={{ color: '#64748b' }}>Total Items:</span>
                  <span style={{ fontWeight: 600 }}>{cartItems.reduce((acc, i) => acc + i.quantity, 0)} units</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.95rem', fontWeight: 700 }}>
                  <span>Total Amount:</span>
                  <span>₹{totalAmount.toLocaleString()}</span>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: 4 }}>
                  Name
                </label>
                <input
                  type="text"
                  required
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: '0.85rem' }}
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: 4 }}>
                  Email
                </label>
                <input
                  type="email"
                  required
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: '0.85rem' }}
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: 4 }}>
                  Address
                </label>
                <input
                  type="text"
                  required
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: '0.85rem' }}
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                />
              </div>

              <button
                type="submit"
                className="checkout-btn"
                style={{ marginTop: 6 }}
              >
                <span>Place Order (₹{totalAmount.toLocaleString()})</span>
                <ArrowRight size={16} />
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
