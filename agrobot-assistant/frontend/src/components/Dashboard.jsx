import React, { useState, useEffect } from 'react';
import { BarChart3, Leaf, Cloud, Settings, Home, TrendingUp, Plus, Loader, Activity } from 'lucide-react';
import CropMonitor from './CropMonitor';
import WeatherWidget from './WeatherWidget';
import AddCropModal from './AddCropModal';
import ApiService from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Dashboard.css';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [recommendations, setRecommendations] = useState(null);
  const [userCrops, setUserCrops] = useState([]); // Start with empty array
  const [schemes, setSchemes] = useState(null);
  const [expandedSchemes, setExpandedSchemes] = useState([]);
  const [showAddCropModal, setShowAddCropModal] = useState(false);
  const [showOverviewStats, setShowOverviewStats] = useState(true);
  const [showCropMonitorBlock, setShowCropMonitorBlock] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const { user, logout } = useAuth();

  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    setExpandedSchemes([]);
  }, [schemes]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load AI recommendations
      try {
        const recs = await ApiService.getLatestRecommendations();
        setRecommendations(recs);
        console.log('Recommendations loaded:', recs);
      } catch (recError) {
        console.log('No recommendations found:', recError.message);
        setRecommendations(null);
      }
      
      // Start with empty crops - user will add them via + button
      setUserCrops([]);

      // Load schemes in background (don't block dashboard initial render)
      ApiService.getGovernmentSchemes()
        .then((schemesResponse) => {
          setSchemes(schemesResponse);
        })
        .catch((schemeErr) => {
          console.log('No government schemes yet:', schemeErr.message);
          setSchemes(null);
        });
      
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddCrop = async (cropData) => {
    try {
      // For now, add to local state (you can implement API later)
      const newCrop = {
        id: Date.now(),
        name: cropData.name,
        variety: cropData.variety,
        area: cropData.area,
        plantingDate: cropData.plantingDate,
        expectedHarvest: cropData.expectedHarvest,
        health: 'Good',
        moisture: Math.floor(Math.random() * 30) + 60, // Random 60-90%
        temperature: Math.floor(Math.random() * 10) + 20, // Random 20-30°C
        status: 'healthy',
        lastUpdated: 'Just now'
      };
      
      setUserCrops(prev => [...prev, newCrop]);
      setShowAddCropModal(false);
    } catch (error) {
      console.error('Error adding crop:', error);
    }
  };

  const handleRemoveCrop = (cropId) => {
    setUserCrops(prev => prev.filter(crop => crop.id !== cropId));
  };

  const parseSchemes = (summaryText) => {
    if (!summaryText) return [];

    const lines = summaryText
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean);

    const schemeItems = [];
    let currentScheme = null;

    const isDetailLine = (text) =>
      /^(brief description|description|eligibility|how to apply|application process|benefits?)\s*:/i.test(
        text
      );

    const pushCurrent = () => {
      if (currentScheme && currentScheme.title) {
        schemeItems.push(currentScheme);
      }
    };

    for (const rawLine of lines) {
      const line = rawLine.replace(/^[-•]\s*/, '').trim();
      const numberedMatch = line.match(/^(\d+)\.\s*(.+)$/);
      const candidate = numberedMatch ? numberedMatch[2].trim() : line;

      if (
        numberedMatch &&
        !isDetailLine(candidate)
      ) {
        pushCurrent();

        const splitByDesc = candidate.split(/\s+-\s+brief description\s*:/i);
        currentScheme = {
          title: splitByDesc[0].trim(),
          details: [],
        };

        if (splitByDesc[1]) {
          currentScheme.details.push(`Brief Description: ${splitByDesc[1].trim()}`);
        }
        continue;
      }

      if (isDetailLine(candidate)) {
        if (!currentScheme) {
          currentScheme = { title: 'Scheme Details', details: [] };
        }
        currentScheme.details.push(candidate);
        continue;
      }

      if (currentScheme) {
        currentScheme.details.push(candidate);
      }
    }

    pushCurrent();

    return schemeItems.filter((item) => item.title && item.title !== 'Scheme Details');
  };

  const toggleScheme = (idx) => {
    setExpandedSchemes((prev) =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const getSchemeCards = () => {
    if (schemes?.schemes && Array.isArray(schemes.schemes) && schemes.schemes.length > 0) {
      return schemes.schemes.map((scheme) => ({
        title: scheme.name,
        details: [
          `Brief Description: ${scheme.brief_description || 'Not specified in source data'}`,
          `Eligibility: ${scheme.eligibility || 'Not specified in source data'}`,
          `How to Apply: ${scheme.how_to_apply || 'Not specified in source data'}`,
        ],
      }));
    }
    return parseSchemes(schemes?.summary || '');
  };

  const getOverviewStats = () => {
    if (!recommendations) {
      return [
        { 
          title: 'Active Fields', 
          value: userCrops.length.toString(), 
          change: userCrops.length === 0 ? 'Add your first crop' : `${userCrops.length} crops monitored`, 
          trend: 'neutral', 
          icon: <Leaf className="stat-icon" /> 
        },
        { 
          title: 'Soil Health', 
          value: 'N/A', 
          change: 'Complete questionnaire for AI analysis', 
          trend: 'neutral', 
          icon: <TrendingUp className="stat-icon" /> 
        },
        { 
          title: 'Recommendations', 
          value: '0', 
          change: 'Generate first AI report', 
          trend: 'neutral', 
          icon: <Cloud className="stat-icon" /> 
        },
        { 
          title: 'Alerts', 
          value: '0', 
          change: 'No issues detected', 
          trend: 'up', 
          icon: <BarChart3 className="stat-icon" /> 
        }
      ];
    }

    return [
      { 
        title: 'Active Fields', 
        value: userCrops.length.toString(), 
        change: `${userCrops.length} crops monitored`, 
        trend: 'up', 
        icon: <Leaf className="stat-icon" /> 
      },
      { 
        title: 'Soil Health', 
        value: `${recommendations.soil_health_score.toFixed(1)}/10`, 
        change: 'Based on AI analysis', 
        trend: recommendations.soil_health_score > 7 ? 'up' : 'warning', 
        icon: <TrendingUp className="stat-icon" /> 
      },
      { 
        title: 'Recommendations', 
        value: recommendations.recommended_crops.length.toString(), 
        change: 'AI-generated crops', 
        trend: 'up', 
        icon: <Cloud className="stat-icon" /> 
      },
      { 
        title: 'Calendar Events', 
        value: recommendations.farming_calendar.length.toString(), 
        change: 'Upcoming activities', 
        trend: 'stable', 
        icon: <BarChart3 className="stat-icon" /> 
      }
    ];
  };

  const handleLogout = () => {
    logout();
  };

  const schemeCards = getSchemeCards();
  const orderedSources = (schemes?.sources || [])
    .filter((src) => src?.url)
    .slice()
    .sort((a, b) => (a.title || '').localeCompare(b.title || ''));

  if (loading) {
    return (
      <div className="dashboard-layout">
        <div className="loading-screen">
          <Loader className="loading-spinner" size={48} />
          <p>Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <Leaf className="logo-icon" />
            <span className="logo-text">AgroBot</span>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Home size={18} />
            <span>Overview</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'crops' ? 'active' : ''}`}
            onClick={() => setActiveTab('crops')}
          >
            <Leaf size={18} />
            <span>Crop Monitor</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'weather' ? 'active' : ''}`}
            onClick={() => setActiveTab('weather')}
          >
            <Cloud size={18} />
            <span>Weather</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <BarChart3 size={18} />
            <span>Analytics</span>
          </button>
          <button
            className="nav-item"
            onClick={() => window.location.href = '/disease-checkup'}
          >
            <Activity size={18} />
            <span>Image Disease Checkup</span>
          </button>
          <button
            className="nav-item"
            onClick={() => window.location.href = '/questionnaire?refill=1'}
          >
            <TrendingUp size={18} />
            <span>Refill Questionnaire</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-name">{user?.full_name}</span>
            <span className="user-email">{user?.email}</span>
          </div>
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div className="header-content">
            <h1 className="page-title">Agricultural Dashboard</h1>
            <p className="page-subtitle">
              {recommendations ? 'AI-powered insights for your farm' : 'Set up your first crop to get started'}
            </p>
          </div>
          <div className="header-actions">
            <button className="btn btn-secondary">Export Data</button>
            <button 
              className="btn btn-primary"
              onClick={() => setShowAddCropModal(true)}
            >
              <Plus size={16} />
              Add Crop
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <p>{error}</p>
            <button onClick={loadDashboardData}>Retry</button>
          </div>
        )}

        <div className="content-area">
          {activeTab === 'overview' && (
            <div className="overview-section">
              <div className="section-toolbar">
                <h3>Overview</h3>
                <button
                  className="section-toggle-btn"
                  onClick={() => setShowOverviewStats(prev => !prev)}
                >
                  {showOverviewStats ? 'Hide Overview' : 'Show Overview'}
                </button>
              </div>

              {showOverviewStats && (
                <div className="overview-stats-horizontal">
                  {getOverviewStats().map((stat, index) => (
                    <div key={index} className="overview-stat-card">
                      <div className="stat-header">
                        {stat.icon}
                        <span className="stat-title">{stat.title}</span>
                      </div>
                      <div className="stat-value">{stat.value}</div>
                      <div className={`stat-change ${stat.trend}`}>
                        {stat.change}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="section-toolbar section-toolbar-secondary">
                <h3>Crop Monitor</h3>
                <button
                  className="section-toggle-btn"
                  onClick={() => setShowCropMonitorBlock(prev => !prev)}
                >
                  {showCropMonitorBlock ? 'Hide Crop Monitor' : 'Show Crop Monitor'}
                </button>
              </div>

              {showCropMonitorBlock && (
                <div className="dashboard-widgets">
                  <div className="widget-row">
                    <div className="widget-large">
                      <CropMonitor 
                        crops={userCrops} 
                        onAddCrop={() => setShowAddCropModal(true)}
                        onRemoveCrop={handleRemoveCrop}
                        recommendations={recommendations}
                      />
                    </div>
                    <div className="widget-medium">
                      <WeatherWidget />
                    </div>
                  </div>
                </div>
              )}

              {schemes && (
                <section className="panel">
                  <div className="panel-header">
                    <h2>Government Schemes</h2>
                    <p>Official programs matched to your questionnaire</p>
                  </div>
                  <div className="schemes-body">
                    <div className="schemes-list">
                      {schemeCards.map((item, idx) => (
                        <div className="scheme-card" key={idx}>
                          <button className="scheme-head" onClick={() => toggleScheme(idx)}>
                            <span className="scheme-title">{item.title}</span>
                            <span className="scheme-toggle">{expandedSchemes.includes(idx) ? '−' : '+'}</span>
                          </button>
                          {expandedSchemes.includes(idx) && (
                            <div className="scheme-details">
                              {item.details.length > 0 ? (
                                <ul>
                                  {item.details.map((detail, detailIdx) => {
                                    const parts = detail.split(':');
                                    if (parts.length > 1) {
                                      const label = parts[0].trim();
                                      const value = parts.slice(1).join(':').trim();
                                      return (
                                        <li key={detailIdx}>
                                          <strong>{label}:</strong> {value}
                                        </li>
                                      );
                                    }
                                    return <li key={detailIdx}>{detail}</li>;
                                  })}
                                </ul>
                              ) : (
                                <p>No additional details available.</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                      {schemeCards.length === 0 && (
                        <div className="schemes-empty">No scheme details available.</div>
                      )}
                    </div>
                    {orderedSources.length > 0 && (
                      <div className="schemes-sources">
                        <h4>Sources</h4>
                        <ul>
                          {orderedSources.map((src, idx) => (
                            <li key={idx} className="source-item">
                              <span className="source-index">{idx + 1}</span>
                              <div className="source-content">
                                <a href={src.url} target="_blank" rel="noreferrer">
                                  {src.title || src.url}
                                </a>
                                {src.domain && <span className="source-domain">{src.domain}</span>}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {recommendations && (
                <div className="ai-recommendations">
                  <h2>🤖 AI Recommendations</h2>
                  <div className="recommendations-grid">
                    <div className="recommendation-card">
                      <h3>🌱 Recommended Crops</h3>
                      <div className="crop-list">
                        {recommendations.recommended_crops.map((crop, index) => (
                          <div key={index} className="crop-item">
                            <div className="crop-details">
                              <strong>{crop.crop_name}</strong> - {crop.variety}
                              <span className="crop-season">{crop.sowing_season}</span>
                            </div>
                            <span className="profitability">Score: {crop.profitability_score}/10</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div className="recommendation-card">
                      <h3>📅 Upcoming Activities</h3>
                      <div className="activity-list">
                        {recommendations.farming_calendar.slice(0, 5).map((event, index) => (
                          <div key={index} className="activity-item">
                            <span className="activity-date">{new Date(event.date).toLocaleDateString()}</span>
                            <div className="activity-details">
                              <span className="activity-name">{event.activity}</span>
                              <span className="activity-desc">{event.description}</span>
                            </div>
                            <span className={`priority ${event.priority}`}>{event.priority}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="recommendation-card">
                      <h3>💡 Soil Improvement Tips</h3>
                      <div className="tips-list">
                        {recommendations.soil_improvement_tips.map((tip, index) => (
                          <div key={index} className="tip-item">
                            {tip}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="recommendation-card">
                      <h3>💧 Irrigation Recommendations</h3>
                      <div className="tips-list">
                        {recommendations.irrigation_recommendations.map((rec, index) => (
                          <div key={index} className="tip-item">
                            {rec}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!recommendations && (
                <div className="no-recommendations">
                  <div className="empty-state">
                    <Leaf size={64} className="empty-icon" />
                    <h3>No AI Recommendations Yet</h3>
                    <p>Complete the questionnaire to get personalized farming recommendations powered by AI.</p>
                    <button 
                      className="btn btn-primary"
                      onClick={() => window.location.href = '/questionnaire'}
                    >
                      Complete Questionnaire
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'crops' && (
            <div className="crops-section">
              <CropMonitor 
                crops={userCrops} 
                onAddCrop={() => setShowAddCropModal(true)}
                onRemoveCrop={handleRemoveCrop}
                recommendations={recommendations}
              />
            </div>
          )}
          
          {activeTab === 'weather' && (
            <div className="weather-section">
              <WeatherWidget />
            </div>
          )}
          
          {activeTab === 'analytics' && (
            <div className="analytics-section">
              <div className="analytics-header">
                <h2>Analytics & Insights</h2>
                <p>Historical data and predictive analytics for better decision making</p>
              </div>
              <div className="analytics-placeholder">
                <div className="placeholder-content">
                  <BarChart3 size={48} className="placeholder-icon" />
                  <h3>Analytics Coming Soon</h3>
                  <p>Historical trends, yield predictions, and advanced analytics will be available here.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="settings-section">
              <div className="settings-header">
                <h2>Settings</h2>
                <p>Manage your account and application preferences</p>
              </div>
              <div className="settings-content">
                <div className="setting-group">
                  <h3>Account Information</h3>
                  <div className="setting-item">
                    <label>Full Name</label>
                    <span>{user?.full_name}</span>
                  </div>
                  <div className="setting-item">
                    <label>Email</label>
                    <span>{user?.email}</span>
                  </div>
                </div>
                
                <div className="setting-group">
                  <h3>Preferences</h3>
                  <div className="setting-item">
                    <label>Temperature Unit</label>
                    <select defaultValue="celsius">
                      <option value="celsius">Celsius (°C)</option>
                      <option value="fahrenheit">Fahrenheit (°F)</option>
                    </select>
                  </div>
                  <div className="setting-item">
                    <label>Area Unit</label>
                    <select defaultValue="hectare">
                      <option value="hectare">Hectare</option>
                      <option value="acre">Acre</option>
                      <option value="bigha">Bigha</option>
                    </select>
                  </div>
                </div>

                <div className="setting-group">
                  <h3>Notifications</h3>
                  <div className="setting-item">
                    <label>
                      <input type="checkbox" defaultChecked />
                      Weather Alerts
                    </label>
                  </div>
                  <div className="setting-item">
                    <label>
                      <input type="checkbox" defaultChecked />
                      Crop Health Notifications
                    </label>
                  </div>
                  <div className="setting-item">
                    <label>
                      <input type="checkbox" defaultChecked />
                      Calendar Reminders
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {showAddCropModal && (
        <AddCropModal
          onClose={() => setShowAddCropModal(false)}
          onAdd={handleAddCrop}
          recommendations={recommendations}
        />
      )}
    </div>
  );
};

export default Dashboard;
