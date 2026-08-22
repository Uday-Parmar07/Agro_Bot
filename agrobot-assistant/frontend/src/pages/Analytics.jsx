import React, { useEffect, useMemo, useState } from 'react';
import { BarChart3, TrendingUp, PieChart, Activity, Download } from 'lucide-react';
import ApiService from '../services/api';
import './Analytics.css';

const Analytics = () => {
  const [timeRange, setTimeRange] = useState('30d');
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadFarms = async () => {
      try {
        const farmList = await ApiService.getFarms();
        setFarms(farmList || []);
        setSelectedFarmId((farmList || [])[0]?.id || null);
      } catch (err) {
        setError('Unable to load farms.');
        setLoading(false);
      }
    };

    loadFarms();
  }, []);

  useEffect(() => {
    if (!selectedFarmId) return;

    const loadAnalytics = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await ApiService.getAnalyticsOverview(selectedFarmId);
        setAnalytics(data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Unable to load analytics.');
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, [selectedFarmId, timeRange]);

  const analyticsData = useMemo(() => {
    const latestScore = analytics?.latest_soil_health_score;
    const adoptionRate = analytics?.recommendation_adoption?.adoption_rate || 0;
    return {
      overview: {
        soilScore: latestScore !== null && latestScore !== undefined ? `${latestScore.toFixed(1)}/10` : 'No data',
        diseaseChecks: `${analytics?.disease_check_count || 0}`,
        activeCrops: `${(analytics?.crop_mix || []).reduce((sum, crop) => sum + crop.active_count, 0)}`,
        adoption: `${Math.round(adoptionRate * 100)}%`,
        weatherSnapshots: `${analytics?.weather_snapshot_count || 0}`,
      },
      cropPerformance: (analytics?.crop_mix || []).map((crop) => ({
        crop: crop.crop_name,
        count: crop.count,
        active: crop.active_count,
        efficiency: crop.count ? Math.round((crop.active_count / crop.count) * 100) : 0,
      })),
      monthlyTrends: (analytics?.soil_score_trend || []).slice(-6).map((point) => {
        const date = new Date(point.date);
        return {
          month: Number.isNaN(date.getTime()) ? point.date : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          soil: point.score,
          scorePct: Math.max(0, Math.min(100, point.score * 10)),
        };
      }),
      diseaseFrequency: analytics?.disease_frequency || [],
    };
  }, [analytics]);

  const timeRanges = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: '1y', label: '1 Year' }
  ];

  return (
    <div className="analytics-page">
      <div className="analytics-container">
        <header className="analytics-header">
          <div className="header-content">
            <h1>Farm Analytics</h1>
            <p>Comprehensive insights into your agricultural operations and performance metrics</p>
          </div>
          <div className="header-controls">
            <div className="time-range-selector">
              {timeRanges.map(range => (
                <button
                  key={range.value}
                  className={`time-btn ${timeRange === range.value ? 'active' : ''}`}
                  onClick={() => setTimeRange(range.value)}
                >
                  {range.label}
                </button>
              ))}
            </div>
            {farms.length > 1 && (
              <select
                className="time-btn"
                value={selectedFarmId || ''}
                onChange={(event) => setSelectedFarmId(Number(event.target.value))}
              >
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>{farm.name}</option>
                ))}
              </select>
            )}
            <button className="btn btn-primary"><Download size={16} />Export Report</button>
          </div>
        </header>

        {loading && <div className="insight-card"><p>Loading analytics...</p></div>}
        {error && <div className="insight-card"><p>{error}</p></div>}

        {!loading && !error && <div className="analytics-overview">
          <div className="overview-card">
            <div className="card-header">
              <h3>Soil Health</h3>
              <TrendingUp className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.soilScore}</div>
            <div className="card-change positive">Latest generated recommendation</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Disease Checks</h3>
              <Activity className="card-icon negative" />
            </div>
            <div className="card-value">{analyticsData.overview.diseaseChecks}</div>
            <div className="card-change negative">Stored leaf analyses</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Active Crops</h3>
              <BarChart3 className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.activeCrops}</div>
            <div className="card-change positive">Persisted dashboard crops</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Adoption</h3>
              <PieChart className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.adoption}</div>
            <div className="card-change positive">Recommended crops added</div>
          </div>
        </div>}

        {!loading && !error && <div className="analytics-charts">
          <div className="chart-section">
            <div className="chart-header">
              <h2>Crop Mix</h2>
              <p>Persisted crops grouped by crop type</p>
            </div>
            <div className="crop-performance-chart">
              {analyticsData.cropPerformance.length === 0 && <p>No crops added yet.</p>}
              {analyticsData.cropPerformance.map((crop, index) => (
                <div key={index} className="crop-bar-item">
                  <div className="crop-info">
                    <span className="crop-name">{crop.crop}</span>
                    <span className="crop-yield">{crop.active}/{crop.count} active</span>
                  </div>
                  <div className="progress-container">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${crop.efficiency}%` }}
                      ></div>
                    </div>
                    <span className="efficiency-badge">
                      {crop.efficiency}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="chart-section">
            <div className="chart-header">
              <h2>Soil Score Trend</h2>
              <p>Scores from generated recommendation snapshots</p>
            </div>
            <div className="trends-chart">
              <div className="chart-legend">
                <div className="legend-item">
                  <div className="legend-color yield"></div>
                  <span>Soil Score</span>
                </div>
              </div>
              <div className="chart-grid">
                {analyticsData.monthlyTrends.length === 0 && <p>No recommendation history yet.</p>}
                {analyticsData.monthlyTrends.map((month, index) => (
                  <div key={index} className="chart-column">
                    <div className="chart-bars">
                      <div 
                        className="chart-bar yield"
                        style={{ height: `${month.scorePct}%` }}
                        title={`Soil score: ${month.soil}/10`}
                      ></div>
                    </div>
                    <span className="chart-label">{month.month}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>}

        {!loading && !error && <div className="insights-section">
          <h2>Key Insights & Recommendations</h2>
          <div className="insights-grid">
            <div className="insight-card">
              <div className="insight-icon positive">
                <TrendingUp size={24} />
              </div>
              <div className="insight-content">
                <h3>Recommendation Adoption</h3>
                <p>{analyticsData.overview.adoption} of the latest recommended crops have been added to this farm.</p>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon warning">
                <Activity size={24} />
              </div>
              <div className="insight-content">
                <h3>Weather History</h3>
                <p>{analyticsData.overview.weatherSnapshots} daily weather snapshot{analyticsData.overview.weatherSnapshots === '1' ? '' : 's'} saved for this farm.</p>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon info">
                <BarChart3 size={24} />
              </div>
              <div className="insight-content">
                <h3>Disease Pattern</h3>
                <p>{analyticsData.diseaseFrequency[0] ? `${analyticsData.diseaseFrequency[0].predicted_class.replace(/_/g, ' ')} is the most frequent check result.` : 'No disease checks have been recorded yet.'}</p>
              </div>
            </div>
          </div>
        </div>}
      </div>
    </div>
  );
};

export default Analytics;
