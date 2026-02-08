import React, { useState } from 'react';

export function SourceCard({ source }) {
  const [expanded, setExpanded] = useState(false);
  
  const text = source.text || '';
  const preview = text.length > 200 ? text.slice(0, 200) + '...' : text;
  const similarity = Math.round((source.similarity || 0) * 100);
  
  return (
    <div className="source-card">
      <div className="source-header">
        <span>Page {source.page_num || 'N/A'} • Rank #{source.rank || 'N/A'}</span>
        <span style={{ 
          color: similarity >= 70 ? 'var(--accent-green)' : 
                 similarity >= 50 ? 'var(--accent-yellow)' : 
                 'var(--text-muted)' 
        }}>
          {similarity}% match
        </span>
      </div>
      <div className="source-text">
        {expanded ? text : preview}
      </div>
      {text.length > 200 && (
        <button 
          onClick={() => setExpanded(!expanded)}
          style={{
            marginTop: '8px',
            background: 'none',
            border: 'none',
            color: 'var(--accent-blue)',
            cursor: 'pointer',
            fontSize: '12px',
            padding: 0,
          }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}
