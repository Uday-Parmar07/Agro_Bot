import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import './FeaturePages.css';

const AdvisorDashboard = () => {
  const [farmers, setFarmers] = useState([]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    ApiService.getAdvisorFarmers()
      .then(setFarmers)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load advisor data.'));
  }, []);

  const loadSummary = async (farmerId) => {
    const data = await ApiService.getAdvisorFarmerSummary(farmerId);
    setSummary(data);
  };

  return (
    <div className="feature-page">
      <div className="feature-container">
        <header className="feature-header">
          <div><h1>Advisor Dashboard</h1><p>Assigned farmer history and risk flags.</p></div>
          <Link className="feature-button secondary" to="/dashboard">Dashboard</Link>
        </header>
        {error && <div className="feature-card">{error}</div>}
        <section className="feature-grid">
          {farmers.map((farmer) => (
            <article key={farmer.farmer_id} className="feature-card">
              <h3>{farmer.full_name}</h3>
              <p>{farmer.email}</p>
              <p>Farms: {farmer.farms_count}</p>
              <p>Latest soil score: {farmer.latest_soil_score ?? 'No data'}</p>
              <p>Disease checks in 30 days: {farmer.disease_checks_30d}</p>
              <button className="feature-button" onClick={() => loadSummary(farmer.farmer_id)}>View Summary</button>
            </article>
          ))}
        </section>
        {summary && (
          <section className="feature-card">
            <h3>{summary.full_name} Summary</h3>
            <p>Disease checks: {summary.disease_checks}</p>
            <p>Weather snapshots: {summary.weather_snapshots}</p>
            <p>Flags: {summary.disease_flags.length ? summary.disease_flags.join(', ') : 'None'}</p>
          </section>
        )}
      </div>
    </div>
  );
};

export default AdvisorDashboard;
