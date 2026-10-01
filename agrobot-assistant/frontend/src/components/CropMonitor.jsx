import React from 'react';
import { Leaf, Plus, AlertCircle, CheckCircle, Droplets, Thermometer } from 'lucide-react';
import './CropMonitor.css';

const CropMonitor = ({ crops = [], onAddCrop, onRemoveCrop, recommendations, showAddButton = true }) => {
  
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
            <p>Add your first crop to get disease detection, irrigation alerts, fertilizer recommendations, and yield guidance.</p>
            {showAddButton && (
              <button 
                className="add-first-crop-btn"
                onClick={onAddCrop}
              >
                <Plus size={20} />
                Add Your First Crop
              </button>
            )}
          </div>
          
          {recommendations && recommendations.recommended_crops && (
            <div className="ai-suggestions">
              <h4>🤖 AI Recommended Crops for Your Farm:</h4>
              <div className="suggestion-list">
                {recommendations.recommended_crops.filter((crop) => crop.overall_suitability_score === null || crop.overall_suitability_score === undefined || Number(crop.overall_suitability_score) > 0).slice(0, 3).map((crop, index) => (
                  <div key={index} className="suggestion-item">
                    <span className="crop-name">{crop.crop_name}</span>
                    <span className="crop-score">Suitability: {crop.suitability_band || 'insufficient data'}</span>
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

  // Health tones come from the Organic ramps, not ad-hoc hexes.
  const healthTone = (health) => {
    switch (health) {
      case 'Excellent':
      case 'Good': return 'tag tag-good';
      case 'Warning': return 'tag tag-caution';
      case 'Critical': return 'tag tag-urgent';
      default: return 'tag tag-unknown';
    }
  };

  return (
    <div className="crop-monitor">
      <div className="monitor-header">
        <div className="header-left">
          <h2>Crop Health Monitor</h2>
          <p>Saved cultivated crops for this farm</p>
        </div>
        {showAddButton && (
          <div className="header-right">
            <button className="add-crop-btn" onClick={onAddCrop}>
              <Plus size={16} />
              Add Crop
            </button>
          </div>
        )}
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
              <span className={`health-badge ${healthTone(crop.health)}`}>
                <Leaf size={14} strokeWidth={2.75} />
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
                  <span className={`metric-value${crop.moisture === null ? ' unknown' : ''}`}>{crop.moisture === null ? 'Not assessed' : `${crop.moisture}%`}</span>
                </div>
              </div>

              <div className="metric-item">
                <div className="metric-icon temperature">
                  <Thermometer size={16} />
                </div>
                <div className="metric-data">
                  <span className="metric-label">Temperature</span>
                  <span className={`metric-value${crop.temperature === null ? ' unknown' : ''}`}>{crop.temperature === null ? 'Not assessed' : `${crop.temperature}°C`}</span>
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
