import React, { useState } from 'react';
import { X, Leaf } from 'lucide-react';
import './AddCropModal.css';

const AddCropModal = ({ onClose, onAdd, recommendations }) => {
  const [cropData, setCropData] = useState({
    name: '',
    variety: '',
    area: '',
    plantingDate: '',
    expectedHarvest: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onAdd(cropData);
  };

  const handleRecommendedCropSelect = (crop) => {
    setCropData({
      ...cropData,
      name: crop.crop_name,
      variety: crop.variety
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Add New Crop</h2>
          <button onClick={onClose} className="close-btn">
            <X size={24} />
          </button>
        </div>

        {recommendations && (
          <div className="recommended-crops">
            <h3>AI Recommended Crops</h3>
            <div className="crop-suggestions">
              {recommendations.recommended_crops.map((crop, index) => (
                <button
                  key={index}
                  className="crop-suggestion"
                  onClick={() => handleRecommendedCropSelect(crop)}
                >
                  <Leaf size={16} />
                  {crop.crop_name} - {crop.variety}
                  <span className="score">Score: {crop.profitability_score}/10</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="crop-form">
          <div className="form-group">
            <label>Crop Name</label>
            <input
              type="text"
              value={cropData.name}
              onChange={(e) => setCropData({...cropData, name: e.target.value})}
              placeholder="e.g., Rice, Wheat, Tomato"
              required
            />
          </div>

          <div className="form-group">
            <label>Variety</label>
            <input
              type="text"
              value={cropData.variety}
              onChange={(e) => setCropData({...cropData, variety: e.target.value})}
              placeholder="e.g., Basmati, HD-2967"
              required
            />
          </div>

          <div className="form-group">
            <label>Area (in acres)</label>
            <input
              type="number"
              value={cropData.area}
              onChange={(e) => setCropData({...cropData, area: e.target.value})}
              placeholder="Enter area"
              required
            />
          </div>

          <div className="form-group">
            <label>Planting Date</label>
            <input
              type="date"
              value={cropData.plantingDate}
              onChange={(e) => setCropData({...cropData, plantingDate: e.target.value})}
              required
            />
          </div>

          <div className="form-group">
            <label>Expected Harvest Date</label>
            <input
              type="date"
              value={cropData.expectedHarvest}
              onChange={(e) => setCropData({...cropData, expectedHarvest: e.target.value})}
              required
            />
          </div>

          <div className="form-actions">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Add Crop
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddCropModal;
