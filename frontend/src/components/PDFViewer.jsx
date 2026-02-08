import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export function PDFViewer({ documentId, onClose }) {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const pdfUrl = `${API_BASE}/documents/${documentId}/file`;

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const onDocumentLoadError = (err) => {
    console.error('PDF load error:', err);
    setError('Failed to load PDF');
    setLoading(false);
  };

  const goToPrevPage = () => {
    setPageNumber((prev) => Math.max(prev - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber((prev) => Math.min(prev + 1, numPages || 1));
  };

  const zoomIn = () => setScale((s) => Math.min(s + 0.2, 3));
  const zoomOut = () => setScale((s) => Math.max(s - 0.2, 0.5));

  return (
    <div className="pdf-viewer">
      <div className="pdf-header">
        <div className="pdf-controls">
          <button className="pdf-btn" onClick={zoomOut} title="Zoom Out">−</button>
          <span className="pdf-zoom">{Math.round(scale * 100)}%</span>
          <button className="pdf-btn" onClick={zoomIn} title="Zoom In">+</button>
        </div>
        <div className="pdf-pagination">
          <button 
            className="pdf-btn" 
            onClick={goToPrevPage} 
            disabled={pageNumber <= 1}
          >
            ←
          </button>
          <span className="pdf-page-info">
            {pageNumber} / {numPages || '?'}
          </span>
          <button 
            className="pdf-btn" 
            onClick={goToNextPage} 
            disabled={pageNumber >= (numPages || 1)}
          >
            →
          </button>
        </div>
        <button className="pdf-close-btn" onClick={onClose} title="Close PDF">
          ✕
        </button>
      </div>

      <div className="pdf-content">
        {loading && (
          <div className="pdf-loading">
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p>Loading PDF...</p>
          </div>
        )}

        {error && (
          <div className="pdf-error">
            <p>{error}</p>
          </div>
        )}

        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading=""
        >
          <Page 
            pageNumber={pageNumber} 
            scale={scale}
            renderTextLayer={false}
            renderAnnotationLayer={false}
          />
        </Document>
      </div>
    </div>
  );
}
