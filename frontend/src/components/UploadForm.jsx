import { useState, useRef } from 'react';
import { Upload, Image as ImageIcon, Send } from 'lucide-react';
import './UploadForm.css';

export default function UploadForm({ languages, onSubmit, disabled, mode }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [lang, setLang] = useState(languages[0]?.code || 'hi');
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => setDragActive(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedFile || disabled) return;
    onSubmit(selectedFile, lang);
    setSelectedFile(null);
    setPreview(null);
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  if (mode === 'batch') {
    return (
      <div className="upload-card">
        <div className="batch-coming-soon">
          <ImageIcon size={40} strokeWidth={1.2} />
          <h2>Batch Processing</h2>
          <p>Batch processing mode will be available soon. Switch to Single mode to process individual images.</p>
        </div>
      </div>
    );
  }

  return (
    <form className="upload-card" onSubmit={handleSubmit}>
      <h2 className="upload-title">
        <Upload size={20} />
        Upload Image for OCR
      </h2>

      {/* Dropzone */}
      <div
        className={`dropzone ${dragActive ? 'drag-active' : ''} ${preview ? 'has-preview' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !preview && inputRef.current?.click()}
      >
        {preview ? (
          <div className="preview-container">
            <img src={preview} alt="Preview" className="preview-image" />
            <div className="preview-info">
              <span className="preview-name">{selectedFile?.name}</span>
              <span className="preview-size">
                {(selectedFile?.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
            <button type="button" className="preview-clear" onClick={handleClear}>
              ×
            </button>
          </div>
        ) : (
          <div className="dropzone-prompt">
            <ImageIcon size={36} strokeWidth={1.3} />
            <p>Drop your image here or <span className="dropzone-link">browse</span></p>
            <span className="dropzone-hint">PNG, JPG, JPEG, TIFF, BMP, WebP — max 50 MB</span>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="file-input"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      {/* Controls Row */}
      <div className="upload-controls">
        <div className="control-group">
          <label className="control-label" htmlFor="lang-select">Language</label>
          <select
            id="lang-select"
            className="lang-select"
            value={lang}
            onChange={(e) => setLang(e.target.value)}
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name} ({l.script})
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className="submit-btn"
          disabled={!selectedFile || disabled}
        >
          <Send size={16} />
          Process Image
        </button>
      </div>
    </form>
  );
}
