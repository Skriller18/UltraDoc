import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Helper to clean up and format piped text as proper markdown tables
function formatPipedText(text) {
  if (!text) return '';
  
  // Split into lines
  const lines = text.split('\n');
  const result = [];
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();
    
    // Check if line looks like a table row (has pipes)
    if (line.includes('|') && !line.match(/^\|[-\s|]+\|$/)) {
      // Clean up the line - remove extra dashes that might be inline
      const cells = line.split('|').filter(c => c.trim() !== '' && !c.match(/^[-\s]+$/));
      
      if (cells.length > 1) {
        // It's likely a table row
        const formattedRow = '| ' + cells.map(c => c.trim()).join(' | ') + ' |';
        
        // Check if previous result was not a table row - add header separator
        const prevLine = result[result.length - 1];
        if (prevLine && prevLine.startsWith('|') && !result[result.length - 1].match(/^\|[-\s|]+\|$/)) {
          // Check if we need to add separator (after first row)
          const prevCells = prevLine.split('|').filter(c => c.trim() !== '');
          if (prevCells.length === cells.length && !result.some(r => r.match(/^\|[-\s|]+\|$/))) {
            // Insert separator before this row
            const separator = '| ' + cells.map(() => '---').join(' | ') + ' |';
            // Find if there's already a separator
            if (!result[result.length - 1]?.includes('---')) {
              result.push(separator);
            }
          }
        }
        
        result.push(formattedRow);
        continue;
      }
    }
    
    // Not a table row, just add as-is
    result.push(line);
  }
  
  return result.join('\n');
}

export function SourceCard({ source }) {
  const [expanded, setExpanded] = useState(false);
  
  const text = source.text || '';
  const displayText = expanded ? text : (text.length > 300 ? text.slice(0, 300) + '...' : text);
  const similarity = Math.round((source.similarity || 0) * 100);
  
  // Apply formatting
  const formattedText = formatPipedText(displayText);
  
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
      <div className="source-text markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {formattedText}
        </ReactMarkdown>
      </div>
      {text.length > 300 && (
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
