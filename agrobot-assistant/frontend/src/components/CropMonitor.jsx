import React from 'react';
import { Leaf, Plus, AlertCircle, CheckCircle, Droplets, Thermometer } from 'lucide-react';
import './CropMonitor.css';

const CropMonitor = ({ crops = [], onAddCrop, onRemoveCrop, recommendations }) => {
  
  if (!crops || crops.length === 0) {
    return (
      <div className="crop-monitor">
        <div className="monitor-header">
          <div className="header-left">
            <h2>Crop Health Monitor</h2>
            <p>Monitor and manage your crops with AI-powered insights</p>
          </div>
        </div>

        <div className="empty-crops-state">
          <div className="empty-content">
            <Leaf size={64} className="empty-icon" />
            <h3>No Crops Added Yet</h3>
            <p>Start by adding your first crop to monitor its health and get AI recommendations</p>
            <button 
              className="add-first-crop-btn"
              onClick={onAddCrop}
            >
              <Plus size={20} />
              Add Your First Crop
            </button>
          </div>
          
          {recommendations && recommendations.recommended_crops && (
            <div className="ai-suggestions">
              <h4>🤖 AI Recommended Crops for Your Farm:</h4>
              <div className="suggestion-list">
                {recommendations.recommended_crops.slice(0, 3).map((crop, index) => (
                  <div key={index} className="suggestion-item">
                    <span className="crop-name">{crop.crop_name} - {crop.variety}</span>
                    <span className="crop-score">Score: {crop.profitability_score}/10</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="status-icon healthy" />;
      case 'warning':
        return <AlertCircle className="status-icon warning" />;
      default:
        return <CheckCircle className="status-icon" />;
    }
  };

  const getHealthColor = (health) => {
    switch (health) {
      case 'Excellent': return '#34d399';
      case 'Good': return '#60a5fa';
      case 'Warning': return '#fbbf24';
      case 'Critical': return '#f87171';
      default: return '#94a3b8';
    }
  };

  return (
    <div className="crop-monitor">
      <div className="monitor-header">
        <div className="header-left">
          <h2>Crop Health Monitor</h2>
          <p>Real-time monitoring of {crops.length} crop{crops.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="header-right">
          <button className="add-crop-btn" onClick={onAddCrop}>
            <Plus size={16} />
            Add Crop
          </button>
        </div>
      </div>

      <div className="crops-grid">
        {crops.map(crop => (
          <div key={crop.id} className="crop-card">
            <div className="crop-header">
              <div className="crop-title">
                <h3>{crop.name}</h3>
                <span className="field-name">{crop.variety}</span>
              </div>
              <div className="crop-actions">
                {getStatusIcon(crop.status)}
                <button 
                  className="remove-crop-btn"
                  onClick={() => onRemoveCrop(crop.id)}
                  title="Remove crop"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="health-indicator">
              <span 
                className="health-badge"
                style={{ 
                  backgroundColor: getHealthColor(crop.health) + '20',
                  color: getHealthColor(crop.health),
                  border: `1px solid ${getHealthColor(crop.health)}40`
                }}
              >
                <Leaf size={14} />
                {crop.health}
              </span>
            </div>

            <div className="crop-metrics">
              <div className="metric-item">
                <div className="metric-icon moisture">
                  <Droplets size={16} />
                </div>
                <div className="metric-data">
                  <span className="metric-label">Soil Moisture</span>
                  <span className="metric-value">{crop.moisture}%</span>
                </div>
              </div>

              <div className="metric-item">
                <div className="metric-icon temperature">
                  <Thermometer size={16} />
                </div>
                <div className="metric-data">
                  <span className="metric-label">Temperature</span>
                  <span className="metric-value">{crop.temperature}°C</span>
                </div>
              </div>
            </div>

            <div className="crop-footer">
              <span className="last-updated">Updated {crop.lastUpdated}</span>
              <span className="crop-area">{crop.area} acres</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CropMonitor;
