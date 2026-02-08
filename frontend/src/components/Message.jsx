import React from 'react';
import { ConfidenceBadge } from './ConfidenceBadge';
import { SourceCard } from './SourceCard';

export function Message({ message }) {
  const isUser = message.role === 'user';
  
  return (
    <div className="message">
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? 'U' : 'AI'}
      </div>
      <div className="message-content">
        <div className="message-text">{message.content}</div>
        
        {!isUser && message.confidence !== undefined && (
          <ConfidenceBadge 
            confidence={message.confidence} 
            details={message.confidenceDetails}
          />
        )}
        
        {!isUser && message.guardrail?.triggered && (
          <div className="guardrail-warning">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            Guardrail triggered: {message.guardrail.reason?.replace(/_/g, ' ')}
          </div>
        )}
        
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="sources-container">
            <div className="sources-label">Sources</div>
            {message.sources.map((source, idx) => (
              <SourceCard key={idx} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function LoadingMessage() {
  return (
    <div className="message">
      <div className="message-avatar assistant">AI</div>
      <div className="message-content">
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}
