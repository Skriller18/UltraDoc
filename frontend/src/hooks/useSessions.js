import { useState, useEffect } from "react";
import { api } from "../utils/api";

export function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  // Load sessions from backend storage (source of truth)
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const docs = await api.listDocuments();
        if (cancelled) return;
        const nextSessions = (docs || []).map((d) => ({
          id: d.document_id, // stable
          documentId: d.document_id,
          documentName: d.filename || d.document_id,
          messages: [],
          extractData: null,
          createdAt: d.created_at,
          meta: d,
        }));
        setSessions(nextSessions);
        setActiveSessionId(nextSessions.length > 0 ? nextSessions[0].id : null);
      } catch (e) {
        console.error("Failed to load documents:", e);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  const createSession = (documentId, documentName, meta = null) => {
    const newSession = {
      id: documentId,
      documentId,
      documentName,
      messages: [],
      extractData: null,
      createdAt: meta?.created_at || new Date().toISOString(),
      meta,
    };
    setSessions((prev) => [newSession, ...prev.filter((s) => s.id !== documentId)]);
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

  const setSessionExtractData = (sessionId, extractData) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id === sessionId) {
          return { ...session, extractData };
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
    setSessionExtractData,
    deleteSession,
  };
}
