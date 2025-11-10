import React, { useState } from 'react';
import { Upload, FileText, Loader2, Download, Merge, Minimize2, X, CheckCircle } from 'lucide-react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('merge');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [quality, setQuality] = useState(85);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    validateAndAddFiles(selectedFiles);
  };

  const validateAndAddFiles = (selectedFiles) => {
    const validFiles = selectedFiles.filter(file => {
      if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
        setError(`File "${file.name}" is not a PDF`);
        return false;
      }
      if (file.size > 50 * 1024 * 1024) { // 50MB limit
        setError(`File "${file.name}" is too large (max 50MB)`);
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      setFiles(prevFiles => [...prevFiles, ...validFiles]);
      setResult(null);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    validateAndAddFiles(droppedFiles);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
    if (files.length === 1) {
      setResult(null);
    }
  };

  const clearAll = () => {
    setFiles([]);
    setResult(null);
    setError(null);
  };

  const mergePDFs = async () => {
    if (files.length < 2) {
      setError('Please select at least 2 PDF files to merge');
      return;
    }

    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/merge`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Merge failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const filename = response.headers.get('content-disposition')
        ?.split('filename=')[1]
        ?.replace(/"/g, '') || 'merged.pdf';
      
      setResult({ url, filename, type: 'merge' });
    } catch (error) {
      setError('Error merging PDFs: ' + error.message);
      console.error('Merge error:', error);
    } finally {
      setLoading(false);
    }
  };

  const compressPDF = async () => {
    if (files.length !== 1) {
      setError('Please select exactly 1 PDF file to compress');
      return;
    }

    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', files[0]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/compress?quality=${quality}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Compression failed');
      }

      const originalSize = response.headers.get('X-Original-Size');
      const compressedSize = response.headers.get('X-Compressed-Size');
      const reduction = response.headers.get('X-Reduction-Percentage');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const filename = response.headers.get('content-disposition')
        ?.split('filename=')[1]
        ?.replace(/"/g, '') || 'compressed.pdf';
      
      setResult({ 
        url, 
        filename, 
        type: 'compress',
        stats: { originalSize, compressedSize, reduction }
      });
    } catch (error) {
      setError('Error compressing PDF: ' + error.message);
      console.error('Compress error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = () => {
    if (activeTab === 'merge') {
      mergePDFs();
    } else {
      compressPDF();
    }
  };

  const downloadFile = () => {
    const a = document.createElement('a');
    a.href = result.url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const switchTab = (tab) => {
    setActiveTab(tab);
    clearAll();
  };

  return (
    <div className="app-container">
      <div className="content-wrapper">
        <div className="card">
          {/* Header */}
          <div className="header">
            <div className="header-content">
              <FileText size={40} />
              <div>
                <h1 className="title">PDF Utilities</h1>
                <p className="subtitle">Professional PDF tools for your everyday needs</p>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="tabs">
            <button
              onClick={() => switchTab('merge')}
              className={`tab ${activeTab === 'merge' ? 'tab-active' : ''}`}
            >
              <Merge size={20} />
              Merge PDFs
            </button>
            <button
              onClick={() => switchTab('compress')}
              className={`tab ${activeTab === 'compress' ? 'tab-active' : ''}`}
            >
              <Minimize2 size={20} />
              Compress PDF
            </button>
          </div>

          {/* Content */}
          <div className="content">
            {/* Tab Description */}
            {activeTab === 'merge' && (
              <div className="description">
                <h3 className="description-title">Merge Multiple PDFs</h3>
                <p className="description-text">
                  Upload 2 or more PDF files to combine them into a single document
                </p>
              </div>
            )}

            {activeTab === 'compress' && (
              <div className="description">
                <h3 className="description-title">Compress PDF File</h3>
                <p className="description-text">
                  Reduce PDF file size while maintaining quality
                </p>
                <div className="quality-slider">
                  <label className="slider-label">
                    Compression Quality: {quality}%
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={quality}
                    onChange={(e) => setQuality(e.target.value)}
                    className="slider"
                  />
                  <div className="slider-labels">
                    <span>Smaller file</span>
                    <span>Better quality</span>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="error-message">
                <X size={20} />
                <span>{error}</span>
                <button onClick={() => setError(null)} className="error-close">
                  ×
                </button>
              </div>
            )}

            {/* Upload Area */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="upload-area"
            >
              <input
                type="file"
                accept="application/pdf"
                multiple={activeTab === 'merge'}
                onChange={handleFileChange}
                className="file-input"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="upload-label">
                <Upload size={48} />
                <p className="upload-title">
                  Drop PDF files here or click to browse
                </p>
                <p className="upload-subtitle">
                  {activeTab === 'merge' ? 'Select multiple PDF files' : 'Select one PDF file'}
                </p>
              </label>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="file-list">
                <div className="file-list-header">
                  <h4 className="file-list-title">Selected Files ({files.length})</h4>
                  <button onClick={clearAll} className="clear-button">
                    Clear All
                  </button>
                </div>
                <div className="files">
                  {files.map((file, index) => (
                    <div key={index} className="file-item">
                      <div className="file-info">
                        <FileText size={20} />
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">({formatBytes(file.size)})</span>
                      </div>
                      <button
                        onClick={() => removeFile(index)}
                        className="remove-button"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Button */}
            {files.length > 0 && !result && (
              <button
                onClick={handleProcess}
                disabled={loading}
                className="action-button"
              >
                {loading ? (
                  <>
                    <Loader2 className="spinner" size={20} />
                    Processing...
                  </>
                ) : (
                  <>
                    {activeTab === 'merge' ? 'Merge PDFs' : 'Compress PDF'}
                  </>
                )}
              </button>
            )}

            {/* Result */}
            {result && (
              <div className="result">
                <div className="result-content">
                  <div className="result-info">
                    <CheckCircle size={24} className="result-icon" />
                    <div>
                      <h4 className="result-title">
                        {result.type === 'merge' ? 'PDFs Merged Successfully!' : 'PDF Compressed Successfully!'}
                      </h4>
                      {result.stats && (
                        <div className="result-stats">
                          <p>Original Size: <strong>{formatBytes(result.stats.originalSize)}</strong></p>
                          <p>Compressed Size: <strong>{formatBytes(result.stats.compressedSize)}</strong></p>
                          <p className="reduction">Reduced by: <strong>{result.stats.reduction}%</strong></p>
                        </div>
                      )}
                    </div>
                  </div>
                  <button onClick={downloadFile} className="download-button">
                    <Download size={20} />
                    Download
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="footer">
          <p>More tools coming soon! Stay tuned for split, rotate, and watermark features.</p>
        </div>
      </div>
    </div>
  );
}

export default App;