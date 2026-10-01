import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import CropMonitor from './CropMonitor';
import MandiPriceTeaser from './MandiPriceTeaser';
import WeatherWidget from './WeatherWidget';
import AddCropModal from './AddCropModal';
import ApiService from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { cultivatedCropSummary, farmerSelectedCrops } from '../utils/dashboard';
import {
  AppTopBar,
  AskAgroBotDialog,
  MobileTabBar,
  MoreSheet,
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

const Dashboard = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const { updateLanguage } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('dashboard');
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [weatherOverview, setWeatherOverview] = useState(null);
  const [questionnaire, setQuestionnaire] = useState({});
  const [userCrops, setUserCrops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddCropModal, setShowAddCropModal] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [recommendationRefreshing, setRecommendationRefreshing] = useState(false);
  const [recommendationError, setRecommendationError] = useState(null);

  useEffect(() => {
    const loadFarms = async () => {
      try {
        const farmList = await ApiService.getFarms();
        setFarms(farmList || []);
        setSelectedFarmId((farmList || [])[0]?.id || null);
      } catch (farmError) {
        setError('Failed to load farms. Please retry.');
        setLoading(false);
      }
    };

    loadFarms();
  }, []);

  useEffect(() => {
    if (!selectedFarmId) return;

    const loadDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [recsResult, weatherResult, questionnaireResult, cropsResult] = await Promise.all([
          ApiService.getLatestRecommendations(selectedFarmId).catch(() => null),
          ApiService.getWeatherOverview(selectedFarmId).catch(() => null),
          ApiService.getUserQuestionnaireResponses(selectedFarmId).catch(() => ({})),
          ApiService.getFarmCrops(selectedFarmId).catch(() => []),
        ]);

        setRecommendations(recsResult);
        setWeatherOverview(weatherResult);
        setQuestionnaire(questionnaireResult || {});
        setUserCrops(farmerSelectedCrops(cropsResult || []).map((crop) => ({
          id: crop.id,
          name: crop.crop_name,
          variety: crop.variety || 'Variety not recorded',
          area: crop.area_acres || 0,
          plantingDate: crop.planting_date,
          expectedHarvest: crop.expected_harvest_date,
          health: 'Not assessed',
          moisture: null,
          temperature: null,
          status: crop.status,
          lastUpdated: 'from saved record',
        })));
      } catch (loadError) {
        setError('Failed to load dashboard data. Please retry.');
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [selectedFarmId]);

  const handleRefreshRecommendations = async () => {
    if (!selectedFarmId) return;
    try {
      setRecommendationRefreshing(true);
      setRecommendationError(null);
      const refreshed = await ApiService.refreshRecommendations(selectedFarmId);
      setRecommendations(refreshed);
    } catch (refreshError) {
      setRecommendationError(refreshError.response?.data?.detail || 'Recommendation generation failed safely.');
    } finally {
      setRecommendationRefreshing(false);
    }
  };

  const handleAddCrop = async (cropData) => {
    if (!selectedFarmId) return;
    try {
      const savedCrop = await ApiService.createFarmCrop({
        farm_id: selectedFarmId,
        crop_name: cropData.name,
        variety: cropData.variety,
        area_acres: Number(cropData.area),
        planting_date: cropData.plantingDate || null,
        expected_harvest_date: cropData.expectedHarvest || null,
        added_by: 'user',
      });
      setUserCrops((prev) => [
        {
          id: savedCrop.id,
          name: savedCrop.crop_name,
          variety: savedCrop.variety || 'Variety not recorded',
          area: savedCrop.area_acres || 0,
          plantingDate: savedCrop.planting_date,
          expectedHarvest: savedCrop.expected_harvest_date,
          health: 'Not assessed',
          moisture: null,
          temperature: null,
          status: savedCrop.status,
          lastUpdated: 'Just now',
        },
        ...prev,
      ]);
      setShowAddCropModal(false);
    } catch (saveError) {
      setError('Failed to save crop. Please retry.');
    }
  };

  const handleRemoveCrop = async (cropId) => {
    try {
      await ApiService.removeFarmCrop(cropId);
      setUserCrops((prev) => prev.filter((crop) => crop.id !== cropId));
    } catch (removeError) {
      setError('Failed to remove crop. Please retry.');
    }
  };

  const weatherData = useMemo(() => {
    const current = weatherOverview?.current || {};
    const firstForecast = (weatherOverview?.forecast || [])[0] || {};
    const rainProbability = Number.isFinite(Number(firstForecast.rain_probability))
      ? Number(firstForecast.rain_probability)
      : null;
    const warning = rainProbability !== null && rainProbability > 60
      ? 'Heavy rain expected tomorrow – delay irrigation.'
      : current.temperature > 34
        ? 'Current temperature is high – check field moisture before irrigating.'
        : '';

    return {
      temperature: current.temperature ?? null,
      windSpeed: current.wind_speed ?? null,
      humidity: current.humidity ?? null,
      rainProbability,
      warning,
      source: current._source || 'unknown',
      available: current.temperature !== undefined || current.humidity !== undefined,
    };
  }, [weatherOverview]);

  const farmSummary = useMemo(() => {
    const set1 = questionnaire?.set_1 || {};
    const set4 = questionnaire?.set_4 || {};
    const mainCrops = cultivatedCropSummary(userCrops);

    return {
      location: [set4?.district, set4?.state].filter(Boolean).join(', ') || 'Not available',
      soilType: set1?.soil_texture || 'Not available',
      farmSize: set4?.total_area ? `${set4.total_area} ${set4.area_unit || 'acre'}` : 'Not available',
      season: set4?.season && set4.season !== 'not_sure' ? set4.season : 'Not specified',
      mainCrops,
    };
  }, [questionnaire, userCrops]);

  const farmHealthScore = useMemo(() => {
    const score = Number(recommendations?.soil_health_score);
    return Number.isFinite(score) && score > 0 ? score : null;
  }, [recommendations]);

  const soilStatus = useMemo(() => {
    if (farmHealthScore === null) return 'Not assessed';
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
        { icon: 'ℹ️', title: 'No assessed tasks', note: 'Add a cultivated crop and its planting date to create a farm schedule.' },
      ];
    }

    return calendar;
  }, [recommendations, weatherData.warning]);

  const alerts = useMemo(() => {
    const result = [];

    if (recommendations?.soil_health_score !== null && recommendations?.soil_health_score !== undefined && recommendations.soil_health_score < 6.5) {
      result.push({
        level: 'warning',
        title: 'Low soil health detected',
        description: 'Soil improvement actions are recommended this week.',
      });
    }

    if (weatherData.rainProbability !== null && weatherData.rainProbability > 60) {
      result.push({
        level: 'urgent',
        title: 'Rain expected tomorrow',
        description: 'Delay irrigation and protect fertilizer application.',
      });
    }

    if (!result.length) {
      result.push({
        level: 'good',
        title: 'No assessed alerts',
        description: 'Add measured farm information to enable condition-based alerts.',
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

  const farmLabel = useMemo(() => {
    const farm = farms.find((item) => item.id === selectedFarmId);
    if (!farm) return null;
    const bits = [farmSummary.farmSize, farmSummary.season]
      .filter((bit) => bit && !/not (available|specified)/i.test(bit));
    return { name: farm.name, detail: bits.join(' · ') || 'Farm overview' };
  }, [farms, selectedFarmId, farmSummary]);

  const goTo = (href) => navigate(href);

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
      <a className="skip-link" href="#main">Skip to content</a>

      <DecisionSidebar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        logout={logout}
        onAddCrop={() => setShowAddCropModal(true)}
        farmId={selectedFarmId}
        farmLabel={farmLabel}
        onNavigate={goTo}
      />

      <div className="main-column">
        <AppTopBar farmLabel={farmLabel} onAsk={() => setAssistantOpen(true)} />

        <main className="main-content" id="main">
        <header className="page-header">
          <div className="dashboard-title-row">
            <div>
              <p className="page-eyebrow">{farmLabel ? farmLabel.name : 'Your farm'}</p>
              <h1 className="page-title">Today on your farm</h1>
              <p className="page-subtitle">{t('dashboard.subtitle')}</p>
            </div>
            <div className="header-actions">
              {farms.length > 1 && (
                <select
                  className="select"
                  aria-label="Choose farm"
                  value={selectedFarmId || ''}
                  onChange={(event) => setSelectedFarmId(Number(event.target.value))}
                >
                  {farms.map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </select>
              )}
              <button type="button" className="btn btn-secondary" onClick={() => setAssistantOpen(true)}>
                Ask AgroBot
              </button>
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
            <StatusCards
              score={farmHealthScore}
              soilStatus={soilStatus}
              alertCount={alerts.filter((alert) => alert.level !== 'good').length}
              taskCount={todayItems.length}
              assessmentRoute={`/questionnaire?refill=1&farm_id=${selectedFarmId}&section=soil-fertility&field=soil_test_done`}
            />

            <div className="decision-grid-3">
              <AlertsPanel alerts={alerts} />
              <WeatherOverview weather={weatherData} />
              <FarmSummary summary={farmSummary} onAddCrop={() => setShowAddCropModal(true)} />
            </div>

            <div className="decision-grid-2">
              <CropMonitor
                crops={userCrops}
                onAddCrop={() => setShowAddCropModal(true)}
                onRemoveCrop={handleRemoveCrop}
                recommendations={recommendations}
                showAddButton={false}
              />
              <CropGrowthProgress stage={growthStage} />
            </div>

            <MandiPriceTeaser
              farmId={selectedFarmId}
              crops={userCrops}
              onAddCrop={() => setShowAddCropModal(true)}
            />

            <CropRecommendationsGrid
              recommendation={recommendations}
              refreshing={recommendationRefreshing}
              error={recommendationError}
              onRefresh={handleRefreshRecommendations}
            />
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
            onRemoveCrop={handleRemoveCrop}
            recommendations={recommendations}
            showAddButton={false}
          />
        )}

        {activeTab === 'weather' && <WeatherWidget farmId={selectedFarmId} />}

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
            <div className="setting-item">
              <label>{t('common.language')}</label>
              <select
                value={user?.preferred_language || 'en'}
                onChange={(event) => updateLanguage(event.target.value)}
              >
                <option value="en">{t('common.english')}</option>
                <option value="hi">{t('common.hindi')}</option>
              </select>
            </div>
          </section>
        )}

        </main>

        <MobileTabBar
          user={user}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          farmId={selectedFarmId}
          onNavigate={goTo}
          onMore={() => setMoreOpen(true)}
          moreOpen={moreOpen}
        />
      </div>

      {moreOpen && (
        <MoreSheet
          user={user}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          farmId={selectedFarmId}
          onNavigate={goTo}
          onClose={() => setMoreOpen(false)}
          logout={logout}
        />
      )}

      {assistantOpen && <AskAgroBotDialog onClose={() => setAssistantOpen(false)} />}

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
