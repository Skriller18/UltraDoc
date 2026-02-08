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
          {(() => {
            const topSimRaw = details.top1_raw ?? details.top1;
            const topSimCal = details.top1_calibrated;
            const agreement = details.agreement_rerank ?? details.agreement;
            const agreementSim = details.agreement_similarity;
            const coverage = details.coverage;
            const kwTop1 = details.keyword_top1;
            const kwBoost = details.keyword_boost;

            const fmtPct = (v) => (typeof v === 'number' && Number.isFinite(v) ? (v * 100).toFixed(1) + '%' : '—');
            const fmtNum = (v) => (typeof v === 'number' && Number.isFinite(v) ? v.toFixed(3) : '—');

            return (
              <>
                <div>Top similarity (raw): {fmtPct(topSimRaw)}</div>
                {topSimCal !== undefined && (
                  <div>Top similarity (cal): {fmtPct(topSimCal)}</div>
                )}
                <div>Agreement (rerank): {fmtPct(agreement)}</div>
                {agreementSim !== undefined && (
                  <div>Agreement (similarity): {fmtPct(agreementSim)}</div>
                )}
                <div>Coverage (heur): {fmtPct(coverage)}</div>
                {kwTop1 !== undefined && (
                  <div>Keyword top1: {fmtPct(kwTop1)}</div>
                )}
                {kwBoost !== undefined && (
                  <div>Keyword boost: {fmtNum(kwBoost)}</div>
                )}
                {details.floor_applied !== undefined && (
                  <div>Floor applied: {details.floor_applied}</div>
                )}
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}
