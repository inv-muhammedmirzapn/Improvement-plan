import React from 'react';
import { CheckCircle2, Info, AlertTriangle } from 'lucide-react';

export default function Toast({ message, type = 'success' }) {
  if (!message) return null;

  return (
    <div className="toast-container">
      <div className="toast">
        {type === 'success' && <CheckCircle2 size={16} color="#34d399" />}
        {type === 'info' && <Info size={16} color="#60a5fa" />}
        {type === 'warning' && <AlertTriangle size={16} color="#fbbf24" />}
        <span>{message}</span>
      </div>
    </div>
  );
}
