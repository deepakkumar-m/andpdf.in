// ============================================
// FILE: frontend/src/App.jsx
// ============================================

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


// ============================================
// FILE: frontend/src/App.css
// ============================================
`
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #e0f2fe 0%, #ddd6fe 100%);
  padding: 2rem;
}

.content-wrapper {
  max-width: 1024px;
  margin: 0 auto;
}

.card {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

/* Header */
.header {
  background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
  padding: 2rem;
  color: white;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title {
  font-size: 2.25rem;
  font-weight: 700;
  margin: 0;
}

.subtitle {
  color: #bfdbfe;
  margin-top: 0.5rem;
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
}

.tab {
  flex: 1;
  padding: 1rem 1.5rem;
  border: none;
  background: none;
  font-size: 1rem;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.tab:hover {
  background: #f9fafb;
}

.tab-active {
  background: #eff6ff;
  color: #2563eb;
  border-bottom: 2px solid #2563eb;
}

/* Content */
.content {
  padding: 2rem;
}

.description {
  margin-bottom: 1.5rem;
}

.description-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.description-text {
  color: #6b7280;
  margin-bottom: 1rem;
}

/* Quality Slider */
.quality-slider {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-top: 1rem;
}

.slider-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.slider {
  width: 100%;
  height: 0.5rem;
  background: #bfdbfe;
  border-radius: 0.5rem;
  outline: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 1.25rem;
  height: 1.25rem;
  background: #2563eb;
  border-radius: 50%;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 1.25rem;
  height: 1.25rem;
  background: #2563eb;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

/* Error Message */
.error-message {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.error-close {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #991b1b;
  cursor: pointer;
  line-height: 1;
}

/* Upload Area */
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 0.75rem;
  padding: 3rem;
  text-align: center;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #2563eb;
  background: #eff6ff;
}

.file-input {
  display: none;
}

.upload-label {
  cursor: pointer;
  display: block;
}

.upload-label svg {
  margin: 0 auto 1rem;
  color: #9ca3af;
}

.upload-title {
  font-size: 1.125rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.upload-subtitle {
  font-size: 0.875rem;
  color: #6b7280;
}

/* File List */
.file-list {
  margin-top: 1.5rem;
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.file-list-title {
  font-weight: 600;
  color: #374151;
}

.clear-button {
  background: none;
  border: none;
  color: #ef4444;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.clear-button:hover {
  color: #dc2626;
}

.files {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #eff6ff;
  padding: 0.75rem;
  border-radius: 0.5rem;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #2563eb;
}

.file-name {
  color: #374151;
  font-weight: 500;
}

.file-size {
  color: #6b7280;
  font-size: 0.875rem;
}

.remove-button {
  background: none;
  border: none;
  color: #ef4444;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.remove-button:hover {
  color: #dc2626;
}

/* Action Button */
.action-button {
  width: 100%;
  margin-top: 1.5rem;
  background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
  color: white;
  padding: 1rem 1.5rem;
  border: none;
  border-radius: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.action-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8 0%, #4338ca 100%);
  transform: translateY(-1px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Result */
.result {
  margin-top: 1.5rem;
  background: #f0fdf4;
  border: 2px solid #86efac;
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.result-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.result-info {
  display: flex;
  gap: 1rem;
  flex: 1;
}

.result-icon {
  color: #16a34a;
  flex-shrink: 0;
}

.result-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #15803d;
  margin-bottom: 0.5rem;
}

.result-stats {
  font-size: 0.875rem;
  color: #166534;
}

.result-stats p {
  margin: 0.25rem 0;
}

.reduction {
  font-weight: 600;
}

.download-button {
  background: #16a34a;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
  flex-shrink: 0;
}

.download-button:hover {
  background: #15803d;
  transform: translateY(-1px);
}

/* Footer */
.footer {
  text-align: center;
  margin-top: 2rem;
  color: #6b7280;
}

.footer p {
  font-size: 0.875rem;
}

/* Responsive */
@media (max-width: 768px) {
  .app-container {
    padding: 1rem;
  }

  .header {
    padding: 1.5rem;
  }

  .title {
    font-size: 1.75rem;
  }

  .content {
    padding: 1.5rem;
  }

  .result-content {
    flex-direction: column;
  }

  .download-button {
    width: 100%;
    justify-content: center;
  }
}
`


// ============================================
// FILE: frontend/src/index.js
// ============================================
`
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
`


// ============================================
// FILE: frontend/src/index.css
// ============================================
`
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}
`


// ============================================
// FILE: frontend/package.json
// ============================================
`
{
  "name": "pdf-utilities-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "lucide-react": "^0.263.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
`


// ============================================
// FILE: frontend/public/index.html
// ============================================
`
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#2563eb" />
    <meta name="description" content="Professional PDF utilities - Merge and compress PDFs online" />
    <title>PDF Utilities - Professional PDF Tools</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
`


// ============================================
// FILE: frontend/.env.example
// ============================================
`
REACT_APP_API_URL=http://localhost:8000
`