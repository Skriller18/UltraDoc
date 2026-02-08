import React from 'react';

export function Sidebar({ sessions, activeSessionId, onSessionClick, onNewSession }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-session-btn" onClick={onNewSession}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Session
        </button>
      </div>
      <div className="sessions-list">
        {sessions.map(session => (
          <div
            key={session.id}
            className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSessionClick(session.id)}
          >
            <svg className="session-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14,2 14,8 20,8"></polyline>
            </svg>
            {session.documentName}
          </div>
        ))}
        {sessions.length === 0 && (
          <div className="empty-state">
            <p className="empty-state-text">No sessions yet</p>
          </div>
        )}
      </div>
    </aside>
  );
}
