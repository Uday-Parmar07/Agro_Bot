import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Leaf, Upload, Activity, ArrowLeft } from 'lucide-react';
import ApiService from '../services/api';
import './DiseaseCheckup.css';

const DiseaseCheckup = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const previewUrl = useMemo(() => {
    if (!file) return '';
    return URL.createObjectURL(file);
  }, [file]);

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    setResult(null);
    setError('');
  };

  const handlePredict = async () => {
    if (!file) {
      setError('Please choose an image first.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await ApiService.predictDiseaseImage(file);
      setResult(response);
    } catch (err) {
      setError(err.response?.data?.detail || 'Prediction failed. Please try again.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="disease-page">
      <header className="disease-header">
        <div className="disease-logo">
          <Leaf className="disease-logo-icon" />
          <span>AgroBot</span>
        </div>
        <Link to="/dashboard" className="disease-back-link">
          <ArrowLeft size={16} />
          Back to Dashboard
        </Link>
      </header>

      <main className="disease-main">
        <section className="disease-card">
          <h1>Image Disease Checkup</h1>
          <p>Upload a plant leaf image to detect possible disease class using your CNN model.</p>

          <label className="upload-box" htmlFor="disease-image-input">
            <Upload size={20} />
            <span>{file ? file.name : 'Choose image (JPG/PNG)'}</span>
          </label>
          <input
            id="disease-image-input"
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="upload-input"
          />

          {previewUrl && (
            <div className="preview-wrap">
              <img src={previewUrl} alt="Plant preview" className="preview-image" />
            </div>
          )}

          <button className="predict-btn" onClick={handlePredict} disabled={loading}>
            {loading ? 'Analyzing...' : 'Check Disease'}
          </button>

          {error && <div className="predict-error">{error}</div>}

          {result && (
            <div className="predict-result">
              <div className="result-title">
                <Activity size={18} />
                Prediction Result
              </div>
              <p><strong>Image:</strong> {result.filename}</p>
              <p><strong>Predicted Class:</strong> {result.predicted_class}</p>
              <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
              <p><strong>Detailed Classification:</strong> {result.detailed_classification}</p>
              <p><strong>Possible Cause:</strong> {result.possible_cause}</p>
              <p><strong>Treatment:</strong> {result.treatment}</p>
              <p><strong>LLM Enhanced:</strong> {result.llm_enhanced ? 'Yes' : 'No (fallback guidance)'}</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default DiseaseCheckup;
