import React from 'react';
import { Home, Sprout, CloudSun, BarChart3, Activity, RefreshCcw, Landmark, Settings, Bell, Plus, CloudRain, Droplets, Wind, Thermometer, MessageCircle } from 'lucide-react';

const priorityClass = (priority) => {
  const value = String(priority || '').toLowerCase();
  if (value === 'high' || value === 'urgent') return 'priority urgent';
  if (value === 'medium') return 'priority warning';
  return 'priority good';
};

export const DecisionSidebar = ({ user, activeTab, setActiveTab, logout, onAddCrop }) => {
  const itemClass = (key) => `nav-item ${activeTab === key ? 'active' : ''}`;

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <Sprout className="logo-icon" />
          <span className="logo-text">AgroBot</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <button className={itemClass('dashboard')} onClick={() => setActiveTab('dashboard')}><Home size={18} /><span>Dashboard</span></button>
        <button className={itemClass('crops')} onClick={() => setActiveTab('crops')}><Sprout size={18} /><span>My Crops</span></button>
        <button className={itemClass('weather')} onClick={() => setActiveTab('weather')}><CloudSun size={18} /><span>Weather</span></button>
        <button className={itemClass('insights')} onClick={() => setActiveTab('insights')}><BarChart3 size={18} /><span>Farm Insights</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/disease-checkup')}><Activity size={18} /><span>Disease Detection</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/questionnaire?refill=1')}><RefreshCcw size={18} /><span>Update Farm Info</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/government-schemes')}><Landmark size={18} /><span>Government Schemes</span></button>
        <button className={itemClass('settings')} onClick={() => setActiveTab('settings')}><Settings size={18} /><span>Settings</span></button>
      </nav>

      <div className="sidebar-quick-actions">
        <h4>Quick Actions</h4>
        <button className="sidebar-action-btn" onClick={onAddCrop}><Plus size={14} /> Add Crop</button>
        <button className="sidebar-action-btn" onClick={() => (window.location.href = '/disease-checkup')}>🔍 Check Disease</button>
        <button className="sidebar-action-btn" onClick={() => setActiveTab('weather')}>🌦 Weather</button>
        <button className="sidebar-action-btn" onClick={() => setActiveTab('insights')}>💧 Irrigation Advice</button>
      </div>

      <div className="sidebar-footer">
        <div className="user-info">
          <span className="user-name">{user?.full_name}</span>
          <span className="user-email">{user?.email}</span>
        </div>
        <button onClick={logout} className="logout-btn">Logout</button>
      </div>
    </aside>
  );
};

export const TodayOnFarm = ({ items }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>Today on Your Farm</h2></div>
    <ul className="today-list">
      {items.map((item, idx) => (
        <li key={idx} className="today-item"><span>{item.icon}</span><div><strong>{item.title}</strong><p>{item.note}</p></div></li>
      ))}
    </ul>
  </section>
);

export const StatusCards = ({ score, soilStatus, alertCount, taskCount }) => {
  const cards = [
    { title: 'Farm Health Score', value: `${score.toFixed(1)} / 10`, tone: score >= 7 ? 'good' : score >= 5 ? 'warning' : 'urgent' },
    { title: 'Soil Health Status', value: soilStatus, tone: soilStatus.toLowerCase().includes('good') ? 'good' : 'warning' },
    { title: 'Alerts / Warnings', value: String(alertCount), tone: alertCount > 0 ? 'warning' : 'good' },
    { title: "Today's Tasks", value: String(taskCount), tone: taskCount > 2 ? 'warning' : 'good' },
  ];
  return (
    <section className="status-grid">
      {cards.map((card, idx) => (
        <article key={idx} className={`status-card ${card.tone}`}>
          <h4>{card.title}</h4>
          <strong>{card.value}</strong>
        </article>
      ))}
    </section>
  );
};

export const AlertsPanel = ({ alerts }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2><Bell size={16} /> Alerts</h2></div>
    <div className="alerts-list">
      {alerts.length === 0 ? <div className="alert-item good">No urgent alerts right now.</div> : alerts.map((alert, idx) => (
        <div key={idx} className={`alert-item ${alert.level}`}><strong>{alert.title}</strong><p>{alert.description}</p></div>
      ))}
    </div>
  </section>
);

export const WeatherOverview = ({ weather }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>Weather Overview</h2></div>
    <div className="weather-kpis">
      <div><Thermometer size={15} /> {Math.round(weather.temperature || 0)}°C</div>
      <div><CloudRain size={15} /> Rain {Math.round(weather.rainProbability || 0)}%</div>
      <div><Wind size={15} /> {Math.round(weather.windSpeed || 0)} km/h</div>
      <div><Droplets size={15} /> {Math.round(weather.humidity || 0)}%</div>
    </div>
    {weather.warning && <div className="weather-warning">{weather.warning}</div>}
  </section>
);

export const FarmSummary = ({ summary }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>Farm Summary</h2></div>
    <div className="summary-grid">
      <div><span>Location</span><strong>{summary.location}</strong></div>
      <div><span>Soil Type</span><strong>{summary.soilType}</strong></div>
      <div><span>Farm Size</span><strong>{summary.farmSize}</strong></div>
      <div><span>Current Season</span><strong>{summary.season}</strong></div>
      <div><span>Main Crops</span><strong>{summary.mainCrops}</strong></div>
    </div>
  </section>
);

export const CropRecommendationsGrid = ({ crops }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>AI Crop Recommendations</h2></div>
    <div className="recommendation-cards">
      {crops.map((crop, idx) => (
        <article key={idx} className="recommendation-card">
          <h4>{crop.crop_name}</h4>
          <p>Variety: {crop.variety}</p>
          <p>Season: {crop.sowing_season}</p>
          <p>Suitability Score: {crop.profitability_score} / 10</p>
        </article>
      ))}
      {crops.length === 0 && <div className="schemes-empty">No recommendations yet. Complete questionnaire to generate.</div>}
    </div>
  </section>
);

export const UpcomingTasks = ({ tasks }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>Upcoming Farm Tasks</h2></div>
    <div className="tasks-list">
      {tasks.map((task, idx) => (
        <div key={idx} className="task-item">
          <div className="task-left"><span className="task-icon">{task.icon}</span><div><strong>{task.dateLabel} — {task.activity}</strong><p>{task.description}</p></div></div>
          <span className={priorityClass(task.priority)}>{task.priority}</span>
        </div>
      ))}
      {tasks.length === 0 && <div className="schemes-empty">No upcoming tasks available.</div>}
    </div>
  </section>
);

export const CropGrowthProgress = ({ stage = 'Vegetative' }) => {
  const stages = ['Seedling', 'Vegetative', 'Flowering', 'Harvest'];
  const activeIndex = Math.max(0, stages.indexOf(stage));

  return (
    <section className="panel decision-panel">
      <div className="panel-header"><h2>Crop Growth Progress</h2></div>
      <div className="growth-track">
        {stages.map((item, idx) => (
          <div key={item} className={`growth-step ${idx <= activeIndex ? 'active' : ''}`}>
            <span className="dot" />
            <small>{item}</small>
          </div>
        ))}
      </div>
    </section>
  );
};

export const AdvicePanels = ({ soilTips, irrigationTips }) => (
  <section className="advice-grid">
    <article className="panel decision-panel"><div className="panel-header"><h2>Soil Improvement Tips</h2></div><ul>{soilTips.slice(0, 5).map((tip, idx) => <li key={idx}>{tip}</li>)}</ul></article>
    <article className="panel decision-panel"><div className="panel-header"><h2>Irrigation Advice</h2></div><ul>{irrigationTips.slice(0, 5).map((tip, idx) => <li key={idx}>{tip}</li>)}</ul></article>
  </section>
);

export const AskAgroBotFab = ({ onClick }) => (
  <button className="ask-agrobot-fab" onClick={onClick}><MessageCircle size={16} /> Ask AgroBot</button>
);
