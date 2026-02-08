import React, { useState, useRef, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { UploadZone } from './components/UploadZone';
import { Message, LoadingMessage } from './components/Message';
import { ExtractPanel } from './components/ExtractPanel';
import { PDFViewer } from './components/PDFViewer';
import { useSessions } from './hooks/useSessions';
import { api } from './utils/api';
import './index.css';

function App() {
  const {
    sessions,
    activeSession,
    activeSessionId,
    createSession,
    switchSession,
    addMessage,
  } = useSessions();

  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [showExtract, setShowExtract] = useState(false);
  const [extractData, setExtractData] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [showPDF, setShowPDF] = useState(true);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeSession?.messages]);

  const handleUpload = async (file) => {
    setIsUploading(true);
    try {
      const result = await api.uploadDocument(file);
      createSession(result.document_id, file.name);
      setShowUpload(false);
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    } finally {
      setIsUploading(false);
    }
  };

  const handleNewSession = () => {
    setShowUpload(true);
  };

  const handleAsk = async () => {
    if (!inputValue.trim() || !activeSession) return;

    const question = inputValue.trim();
    setInputValue('');

    // Add user message
    addMessage(activeSessionId, {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: question,
    });

    setIsAsking(true);

    try {
      const response = await api.askQuestion(activeSession.documentId, question);
      
      addMessage(activeSessionId, {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        confidence: response.confidence,
        confidenceDetails: response.confidence_details,
        sources: response.sources,
        guardrail: response.guardrail,
      });
    } catch (error) {
      console.error('Ask failed:', error);
      addMessage(activeSessionId, {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
      });
    } finally {
      setIsAsking(false);
    }
  };

  const handleExtract = async () => {
    if (!activeSession) return;
    
    setShowExtract(true);
    setIsExtracting(true);
    setExtractData(null);

    try {
      const data = await api.extractData(activeSession.documentId);
      setExtractData(data);
    } catch (error) {
      console.error('Extraction failed:', error);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSessionClick={switchSession}
        onNewSession={handleNewSession}
      />

      <main className="main-content">
        <header className="header">
          <div className="header-left">
            <h1 className="header-title">
              {activeSession ? activeSession.documentName : 'UltraDoc AI'}
            </h1>
            {activeSession && (
              <button 
                className="action-btn secondary toggle-pdf-btn" 
                onClick={() => setShowPDF(!showPDF)}
              >
                {showPDF ? '📄 Hide PDF' : '📄 Show PDF'}
              </button>
            )}
          </div>
          {activeSession && (
            <button className="action-btn secondary" onClick={handleExtract}>
              Extract Data
            </button>
          )}
        </header>

        <div className={`content-area ${activeSession && showPDF ? 'split-view' : ''}`}>
          {/* PDF Viewer Panel */}
          {activeSession && showPDF && !showUpload && (
            <PDFViewer 
              documentId={activeSession.documentId} 
              onClose={() => setShowPDF(false)}
            />
          )}

          {/* Chat Panel */}
          <div className="chat-panel">
            <div className="chat-container">
              {!activeSession && !showUpload && (
                <div className="empty-state">
                  <div className="empty-state-icon">📄</div>
                  <h2 className="empty-state-title">Welcome to UltraDoc AI</h2>
                  <p className="empty-state-text">
                    Upload a logistics document to start asking questions
                  </p>
                  <button
                    className="action-btn primary"
                    style={{ marginTop: '20px' }}
                    onClick={handleNewSession}
                  >
                    Upload Document
                  </button>
                </div>
              )}

              {showUpload && (
                <UploadZone onUpload={handleUpload} isUploading={isUploading} />
              )}

              {activeSession && !showUpload && (
                <div className="messages-list">
                  {activeSession.messages.length === 0 && (
                    <div className="empty-state">
                      <p className="empty-state-text">
                        Ask a question about your document
                      </p>
                    </div>
                  )}
                  {activeSession.messages.map((msg) => (
                    <Message key={msg.id} message={msg} />
                  ))}
                  {isAsking && <LoadingMessage />}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {activeSession && !showUpload && (
              <div className="input-container">
                <div className="input-wrapper">
                  <input
                    type="text"
                    className="chat-input"
                    placeholder="Ask a question about the document..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isAsking}
                  />
                  <div className="input-actions">
                    <button
                      className="action-btn primary"
                      onClick={handleAsk}
                      disabled={!inputValue.trim() || isAsking}
                    >
                      Ask
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {showExtract && (
        <ExtractPanel
          data={extractData}
          isLoading={isExtracting}
          onClose={() => setShowExtract(false)}
        />
      )}
    </div>
  );
}

export default App;
