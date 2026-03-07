import React, { useEffect, useMemo, useState } from 'react';
import CropMonitor from './CropMonitor';
import WeatherWidget from './WeatherWidget';
import AddCropModal from './AddCropModal';
import ApiService from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  AskAgroBotFab,
  CropGrowthProgress,
  CropRecommendationsGrid,
  DecisionSidebar,
  FarmSummary,
  StatusCards,
  TodayOnFarm,
  UpcomingTasks,
  WeatherOverview,
  AlertsPanel,
  AdvicePanels,
} from './dashboard/DecisionWidgets';
import './Dashboard.css';
import './dashboard/DecisionWidgets.css';

const iconForCategory = (category, activity) => {
  const text = `${category || ''} ${activity || ''}`.toLowerCase();
  if (text.includes('land')) return '🚜';
  if (text.includes('sow')) return '🌱';
  if (text.includes('irrig')) return '💧';
  if (text.includes('fertil')) return '🧪';
  if (text.includes('pest')) return '🐛';
  return '✅';
};

const seasonFromMonth = (month) => {
  if ([6, 7, 8, 9, 10].includes(month)) return 'Kharif';
  if ([11, 12, 1, 2, 3].includes(month)) return 'Rabi';
  return 'Zaid';
};

const Dashboard = () => {
  const { user, logout } = useAuth();

  const [activeTab, setActiveTab] = useState('dashboard');
  const [recommendations, setRecommendations] = useState(null);
  const [weatherOverview, setWeatherOverview] = useState(null);
  const [questionnaire, setQuestionnaire] = useState({});
  const [userCrops, setUserCrops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddCropModal, setShowAddCropModal] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [recsResult, weatherResult, questionnaireResult] = await Promise.all([
          ApiService.getLatestRecommendations().catch(() => null),
          ApiService.getWeatherOverview().catch(() => null),
          ApiService.getUserQuestionnaireResponses().catch(() => ({})),
        ]);

        setRecommendations(recsResult);
        setWeatherOverview(weatherResult);
        setQuestionnaire(questionnaireResult || {});
        setUserCrops([]);
      } catch (loadError) {
        setError('Failed to load dashboard data. Please retry.');
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const handleAddCrop = (cropData) => {
    const newCrop = {
      id: Date.now(),
      name: cropData.name,
      variety: cropData.variety,
      area: cropData.area,
      plantingDate: cropData.plantingDate,
      expectedHarvest: cropData.expectedHarvest,
      health: 'Good',
      moisture: Math.floor(Math.random() * 30) + 60,
      temperature: Math.floor(Math.random() * 10) + 20,
      status: 'healthy',
      lastUpdated: 'Just now',
    };
    setUserCrops((prev) => [...prev, newCrop]);
    setShowAddCropModal(false);
  };

  const weatherData = useMemo(() => {
    const current = weatherOverview?.current || {};
    const firstForecast = (weatherOverview?.forecast || [])[0] || {};
    const forecastDesc = `${firstForecast.description || ''}`.toLowerCase();
    const rainProbability = forecastDesc.includes('rain') ? 70 : 20;
    const warning = rainProbability > 60
      ? 'Heavy rain expected tomorrow – delay irrigation.'
      : current.temperature > 34
        ? 'High temperature forecast – irrigate in early morning.'
        : '';

    return {
      temperature: Number(current.temperature || 0),
      windSpeed: Number(current.wind_speed || 0),
      humidity: Number(current.humidity || 0),
      rainProbability,
      warning,
    };
  }, [weatherOverview]);

  const farmSummary = useMemo(() => {
    const set1 = questionnaire?.set_1 || {};
    const set4 = questionnaire?.set_4 || {};
    const mainCrops = (recommendations?.recommended_crops || []).slice(0, 2).map((crop) => crop.crop_name).join(', ') || 'Not available';

    const month = new Date().getMonth() + 1;
    return {
      location: [set4?.district, set4?.state].filter(Boolean).join(', ') || 'Not available',
      soilType: set1?.soil_texture || 'Not available',
      farmSize: set4?.total_area ? `${set4.total_area} ${set4.area_unit || 'acre'}` : 'Not available',
      season: seasonFromMonth(month),
      mainCrops,
    };
  }, [questionnaire, recommendations]);

  const farmHealthScore = useMemo(() => {
    const soil = Number(recommendations?.soil_health_score || 6.4);
    const humidity = weatherData.humidity || 60;
    const water = Math.max(4, 10 - Math.abs(humidity - 65) / 8);
    const weatherRisk = weatherData.warning ? 5.8 : 8.4;
    return (soil * 0.5) + (water * 0.25) + (weatherRisk * 0.25);
  }, [recommendations, weatherData]);

  const soilStatus = useMemo(() => {
    if (farmHealthScore >= 7.5) return 'Good';
    if (farmHealthScore >= 6) return 'Attention Needed';
    return 'Critical';
  }, [farmHealthScore]);

  const todayItems = useMemo(() => {
    const calendar = (recommendations?.farming_calendar || []).slice(0, 3).map((event) => ({
      icon: iconForCategory(event.category, event.activity),
      title: event.activity,
      note: event.description,
    }));

    if (weatherData.warning) {
      calendar.unshift({
        icon: '⚠️',
        title: 'Weather attention',
        note: weatherData.warning,
      });
    }

    if (calendar.length === 0) {
      return [
        { icon: '💧', title: 'Check soil moisture', note: 'Use manual field check this morning.' },
        { icon: '🌱', title: 'Plan sowing', note: 'Review best crop and sowing window.' },
        { icon: '🧪', title: 'Fertilizer prep', note: 'Keep fertilizer ready for scheduled application.' },
      ];
    }

    return calendar;
  }, [recommendations, weatherData.warning]);

  const alerts = useMemo(() => {
    const result = [];

    if ((recommendations?.soil_health_score || 7) < 6.5) {
      result.push({
        level: 'warning',
        title: 'Low soil health detected',
        description: 'Soil improvement actions are recommended this week.',
      });
    }

    if (weatherData.rainProbability > 60) {
      result.push({
        level: 'urgent',
        title: 'Rain expected tomorrow',
        description: 'Delay irrigation and protect fertilizer application.',
      });
    }

    if (!result.length) {
      result.push({
        level: 'good',
        title: 'Farm conditions stable',
        description: 'No major issues detected from current data.',
      });
    }

    return result;
  }, [recommendations, weatherData]);

  const upcomingTasks = useMemo(() => {
    return (recommendations?.farming_calendar || []).slice(0, 5).map((event) => ({
      icon: iconForCategory(event.category, event.activity),
      activity: event.activity,
      description: event.description,
      priority: event.priority || 'medium',
      dateLabel: event.date ? new Date(event.date).toLocaleDateString() : 'Upcoming',
    }));
  }, [recommendations]);

  const growthStage = useMemo(() => {
    if (!userCrops.length) return 'Seedling';
    const firstCrop = userCrops[0];
    if (!firstCrop.plantingDate) return 'Vegetative';

    const days = Math.floor((Date.now() - new Date(firstCrop.plantingDate).getTime()) / (1000 * 60 * 60 * 24));
    if (days < 20) return 'Seedling';
    if (days < 45) return 'Vegetative';
    if (days < 75) return 'Flowering';
    return 'Harvest';
  }, [userCrops]);

  if (loading) {
    return (
      <div className="dashboard-layout">
        <div className="loading-screen">
          <p>Loading your decision dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-layout decision-layout">
      <DecisionSidebar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        logout={logout}
        onAddCrop={() => setShowAddCropModal(true)}
      />

      <main className="main-content">
        <header className="page-header">
          <div className="dashboard-title-row">
            <div>
              <h1 className="page-title">AgroBot Dashboard</h1>
              <p className="page-subtitle">Daily farming decisions, alerts, and crop actions in one place</p>
            </div>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <p>{error}</p>
          </div>
        )}

        {activeTab === 'dashboard' && (
          <>
            <TodayOnFarm items={todayItems} />
            <StatusCards score={farmHealthScore} soilStatus={soilStatus} alertCount={alerts.length} taskCount={todayItems.length} />

            <div className="decision-grid-3">
              <AlertsPanel alerts={alerts} />
              <WeatherOverview weather={weatherData} />
              <FarmSummary summary={farmSummary} />
            </div>

            <div className="decision-grid-2">
              <CropMonitor
                crops={userCrops}
                onAddCrop={() => setShowAddCropModal(true)}
                onRemoveCrop={(cropId) => setUserCrops((prev) => prev.filter((crop) => crop.id !== cropId))}
                recommendations={recommendations}
                showAddButton={false}
              />
              <CropGrowthProgress stage={growthStage} />
            </div>

            <CropRecommendationsGrid crops={recommendations?.recommended_crops || []} />
            <UpcomingTasks tasks={upcomingTasks} />
            <AdvicePanels
              soilTips={recommendations?.soil_improvement_tips || []}
              irrigationTips={recommendations?.irrigation_recommendations || []}
            />
          </>
        )}

        {activeTab === 'crops' && (
          <CropMonitor
            crops={userCrops}
            onAddCrop={() => setShowAddCropModal(true)}
            onRemoveCrop={(cropId) => setUserCrops((prev) => prev.filter((crop) => crop.id !== cropId))}
            recommendations={recommendations}
            showAddButton={false}
          />
        )}

        {activeTab === 'weather' && <WeatherWidget />}

        {activeTab === 'insights' && (
          <>
            <UpcomingTasks tasks={upcomingTasks} />
            <AdvicePanels
              soilTips={recommendations?.soil_improvement_tips || []}
              irrigationTips={recommendations?.irrigation_recommendations || []}
            />
          </>
        )}

        {activeTab === 'settings' && (
          <section className="panel settings-section">
            <h2>Settings</h2>
            <p>Manage your account and preferences.</p>
          </section>
        )}

        <AskAgroBotFab onClick={() => setAssistantOpen((prev) => !prev)} />

        {assistantOpen && (
          <section className="assistant-panel">
            <h3>Ask AgroBot</h3>
            <p>Quick help for daily decisions.</p>
            <div className="assistant-prompt-list">
              <button>When should I irrigate my field?</button>
              <button>Which crop suits my soil?</button>
              <button>How to treat this disease?</button>
            </div>
          </section>
        )}
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
