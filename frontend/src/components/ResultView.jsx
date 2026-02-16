import { useState } from 'react';
import {
  ArrowLeft,
  FileText,
  BarChart3,
  Image as ImageIcon,
  Eye,
  EyeOff,
  Clock,
  Globe,
} from 'lucide-react';
import './ResultView.css';

export default function ResultView({ result, annotatedImageUrl, onBack }) {
  const [showImage, setShowImage] = useState(true);
  const [showText, setShowText] = useState(true);
  const [showConfidence, setShowConfidence] = useState(true);

  if (!result) return null;

  const langLabel = (code) => {
    const map = { hi: 'Hindi', mr: 'Marathi', te: 'Telugu', ta: 'Tamil', ml: 'Malayalam' };
    return map[code] || code;
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.85) return 'confidence-high';
    if (score >= 0.6) return 'confidence-mid';
    return 'confidence-low';
  };

  const avgConfidence =
    result.results && result.results.length > 0
      ? (result.results.reduce((sum, r) => sum + r.confidence, 0) / result.results.length)
      : null;

  return (
    <div className="result-view">
      {/* Top Bar */}
      <div className="result-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={18} />
          New Upload
        </button>

        <div className="result-meta">
          <span className="meta-tag">
            <Globe size={13} />
            {langLabel(result.language)}
          </span>
          <span className="meta-tag">
            <FileText size={13} />
            {result.filename}
          </span>
          {result.processing_time_seconds && (
            <span className="meta-tag">
              <Clock size={13} />
              {result.processing_time_seconds.toFixed(1)}s
            </span>
          )}
          {avgConfidence !== null && (
            <span className={`meta-tag ${getConfidenceColor(avgConfidence)}`}>
              <BarChart3 size={13} />
              Avg {(avgConfidence * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {/* Annotated Image */}
      <div className="result-section">
        <div className="section-header">
          <h3>
            <ImageIcon size={16} />
            Annotated Image
          </h3>
          <button
            className="toggle-btn"
            onClick={() => setShowImage(!showImage)}
            title={showImage ? 'Hide' : 'Show'}
          >
            {showImage ? <EyeOff size={15} /> : <Eye size={15} />}
            {showImage ? 'Hide' : 'Show'}
          </button>
        </div>
        {showImage && (
          <div className="image-container">
            {annotatedImageUrl ? (
              <img src={annotatedImageUrl} alt="Annotated OCR result" />
            ) : (
              <div className="no-image">
                <ImageIcon size={32} strokeWidth={1.2} />
                <p>No annotated image available</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Row: Text + Confidence */}
      <div className="result-bottom-row">
        {/* Extracted Text */}
        <div className="result-section result-half">
          <div className="section-header">
            <h3>
              <FileText size={16} />
              Extracted Text
            </h3>
            <button
              className="toggle-btn"
              onClick={() => setShowText(!showText)}
              title={showText ? 'Hide' : 'Show'}
            >
              {showText ? <EyeOff size={15} /> : <Eye size={15} />}
              {showText ? 'Hide' : 'Show'}
            </button>
          </div>
          {showText && (
            <div className="text-container">
              <pre className="extracted-text">
                {result.full_text || '(No text extracted)'}
              </pre>
            </div>
          )}
        </div>

        {/* Confidence Scores */}
        <div className="result-section result-half">
          <div className="section-header">
            <h3>
              <BarChart3 size={16} />
              Confidence Scores
            </h3>
            <button
              className="toggle-btn"
              onClick={() => setShowConfidence(!showConfidence)}
              title={showConfidence ? 'Hide' : 'Show'}
            >
              {showConfidence ? <EyeOff size={15} /> : <Eye size={15} />}
              {showConfidence ? 'Hide' : 'Show'}
            </button>
          </div>
          {showConfidence && (
            <div className="confidence-container">
              {result.results && result.results.length > 0 ? (
                <div className="confidence-list">
                  {result.results.map((r, idx) => (
                    <div key={idx} className="confidence-row">
                      <span className="confidence-text" title={r.text}>
                        {r.text}
                      </span>
                      <div className="confidence-bar-wrapper">
                        <div
                          className={`confidence-bar ${getConfidenceColor(r.confidence)}`}
                          style={{ width: `${(r.confidence * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <span className={`confidence-value ${getConfidenceColor(r.confidence)}`}>
                        {(r.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-confidence">
                  <p>No per-region confidence data available</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
