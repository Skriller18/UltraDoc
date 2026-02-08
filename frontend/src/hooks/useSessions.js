import { useState, useEffect } from "react";

const STORAGE_KEY = "ultradoc_sessions";

// Helper to load sessions from localStorage
function loadStoredSessions() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch (e) {
      console.error("Failed to parse sessions:", e);
    }
  }
  return [];
}

export function useSessions() {
  // Use lazy initialization - the function is only called once on mount
  const [sessions, setSessions] = useState(() => loadStoredSessions());
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const stored = loadStoredSessions();
    return stored.length > 0 ? stored[0].id : null;
  });

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  const createSession = (documentId, documentName) => {
    const newSession = {
      id: `session_${Date.now()}`,
      documentId,
      documentName,
      messages: [],
      createdAt: new Date().toISOString(),
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    return newSession;
  };

  const switchSession = (sessionId) => {
    setActiveSessionId(sessionId);
  };

  const addMessage = (sessionId, message) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id === sessionId) {
          return {
            ...session,
            messages: [...session.messages, message],
          };
        }
        return session;
      }),
    );
  };

  const deleteSession = (sessionId) => {
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId);
      if (activeSessionId === sessionId && filtered.length > 0) {
        setActiveSessionId(filtered[0].id);
      } else if (filtered.length === 0) {
        setActiveSessionId(null);
      }
      return filtered;
    });
  };

  return {
    sessions,
    activeSession,
    activeSessionId,
    createSession,
    switchSession,
    addMessage,
    deleteSession,
  };
}
