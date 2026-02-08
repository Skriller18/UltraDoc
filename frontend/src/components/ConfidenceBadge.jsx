import React, { useState } from 'react';

export function ConfidenceBadge({ confidence, details }) {
  const [showTooltip, setShowTooltip] = useState(false);
  
  const percentage = Math.round(confidence * 100);
  
  let level = 'low';
  if (percentage >= 75) level = 'high';
  else if (percentage >= 50) level = 'medium';
  
  return (
    <div 
      className={`confidence-badge ${level}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{ position: 'relative', cursor: 'help' }}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>
      Confidence: {percentage}%
      
      {showTooltip && details && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          padding: '10px 12px',
          backgroundColor: 'var(--bg-tertiary)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '12px',
          whiteSpace: 'nowrap',
          zIndex: 10,
        }}>
          <div style={{ marginBottom: '4px' }}>
            <strong>Breakdown:</strong>
          </div>
          <div>Top similarity: {(details.top1 * 100).toFixed(1)}%</div>
          <div>Agreement: {(details.agreement * 100).toFixed(1)}%</div>
          <div>Coverage: {(details.coverage * 100).toFixed(1)}%</div>
        </div>
      )}
    </div>
  );
}
