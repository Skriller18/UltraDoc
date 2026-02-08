import React, { useState, useRef } from 'react';

export function UploadZone({ onUpload, isUploading }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFile = async (file) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ];
    
    const ext = file.name.split('.').pop().toLowerCase();
    const isValidExt = ['pdf', 'docx', 'txt'].includes(ext);
    
    if (!validTypes.includes(file.type) && !isValidExt) {
      alert('Please upload a PDF, DOCX, or TXT file');
      return;
    }
    
    // Simulate progress for UX
    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval);
          return prev;
        }
        return prev + 10;
      });
    }, 100);
    
    try {
      await onUpload(file);
      setUploadProgress(100);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      clearInterval(interval);
      setTimeout(() => setUploadProgress(0), 500);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      className={`upload-zone ${isDragging ? 'dragging' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.docx,.txt"
        style={{ display: 'none' }}
      />
      
      <div className="upload-icon">📄</div>
      <h3 className="upload-title">
        {isUploading ? 'Uploading...' : 'Upload a Document'}
      </h3>
      <p className="upload-subtitle">
        Drag and drop or click to browse
        <br />
        Supports PDF, DOCX, TXT
      </p>
      
      {uploadProgress > 0 && (
        <div className="upload-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
          </div>
        </div>
      )}
    </div>
  );
}
