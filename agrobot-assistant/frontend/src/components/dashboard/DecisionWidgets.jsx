import React from 'react';
import { Home, Sprout, CloudSun, BarChart3, Activity, RefreshCcw, Landmark, Settings, Bell, Plus, CloudRain, Droplets, Wind, Thermometer, MessageCircle, UserCheck, IndianRupee } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const priorityClass = (priority) => {
  const value = String(priority || '').toLowerCase();
  if (value === 'high' || value === 'urgent') return 'priority urgent';
  if (value === 'medium') return 'priority warning';
  return 'priority good';
};

export const DecisionSidebar = ({ user, activeTab, setActiveTab, logout, onAddCrop, farmId }) => {
  const { t } = useTranslation();
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
        <button className={itemClass('dashboard')} onClick={() => setActiveTab('dashboard')}><Home size={18} /><span>{t('nav.dashboard')}</span></button>
        <button className={itemClass('crops')} onClick={() => setActiveTab('crops')}><Sprout size={18} /><span>{t('nav.crops')}</span></button>
        <button className={itemClass('weather')} onClick={() => setActiveTab('weather')}><CloudSun size={18} /><span>{t('nav.weather')}</span></button>
        <button className={itemClass('insights')} onClick={() => setActiveTab('insights')}><BarChart3 size={18} /><span>{t('nav.insights')}</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/analytics')}><BarChart3 size={18} /><span>{t('nav.analytics')}</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/disease-checkup')}><Activity size={18} /><span>{t('nav.disease')}</span></button>
        <button className="nav-item" onClick={() => (window.location.href = `/questionnaire?refill=1${farmId ? `&farm_id=${farmId}` : ''}`)}><RefreshCcw size={18} /><span>{t('nav.questionnaire')}</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/government-schemes')}><Landmark size={18} /><span>{t('nav.schemes')}</span></button>
        <button className="nav-item" onClick={() => (window.location.href = '/mandi-prices')}><IndianRupee size={18} /><span>{t('nav.mandiPrices')}</span></button>
        {['advisor', 'admin'].includes(user?.role) && <button className="nav-item" onClick={() => (window.location.href = '/advisor')}><UserCheck size={18} /><span>{t('nav.advisor')}</span></button>}
        <button className={itemClass('settings')} onClick={() => setActiveTab('settings')}><Settings size={18} /><span>{t('nav.settings')}</span></button>
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
        <button onClick={logout} className="logout-btn">{t('nav.logout')}</button>
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

export const StatusCards = ({ score, soilStatus, alertCount, taskCount, assessmentRoute }) => {
  const cards = [
    { title: 'Farm Health Score', value: score === null ? 'Not assessed' : `${score.toFixed(1)} / 10`, tone: score === null ? 'warning' : score >= 7 ? 'good' : score >= 5 ? 'warning' : 'urgent' },
    { title: 'Soil Health Status', value: soilStatus, tone: soilStatus.toLowerCase().includes('good') ? 'good' : 'warning' },
    { title: 'Alerts / Warnings', value: String(alertCount), tone: alertCount > 0 ? 'warning' : 'good' },
    { title: "Today's Tasks", value: String(taskCount), tone: taskCount > 2 ? 'warning' : 'good' },
  ];
  return (
    <section className="status-section">
      <div className="status-grid">
        {cards.map((card, idx) => (
          <article key={idx} className={`status-card ${card.tone}`}>
            <h4>{card.title}</h4>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
      {score === null && (
        <div className="assessment-empty">
          <div><strong>Farm health not assessed</strong><p>Complete farm details or add a soil test to generate an assessment.</p></div>
          <a className="recommendation-action" href={assessmentRoute}>Complete assessment</a>
        </div>
      )}
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
    {!weather.available ? <div className="weather-warning">Weather unavailable</div> : <>
      {weather.source === 'mock_fallback' && <div className="weather-warning">Development mock weather — not live conditions</div>}
      <div className="weather-kpis">
        <div><Thermometer size={15} /> {weather.temperature === null ? 'Unavailable' : `${Math.round(weather.temperature)}°C`}</div>
        <div><CloudRain size={15} /> Rain {weather.rainProbability === null ? 'Unavailable' : `${Math.round(weather.rainProbability)}%`}</div>
        <div><Wind size={15} /> {weather.windSpeed === null ? 'Unavailable' : `${Math.round(weather.windSpeed)} km/h`}</div>
        <div><Droplets size={15} /> {weather.humidity === null ? 'Unavailable' : `${Math.round(weather.humidity)}%`}</div>
      </div>
    </>}
    {weather.warning && <div className="weather-warning">{weather.warning}</div>}
  </section>
);

export const FarmSummary = ({ summary, onAddCrop }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2>Farm Summary</h2></div>
    <div className="summary-grid">
      <div><span>Location</span><strong>{summary.location}</strong></div>
      <div><span>Soil Type</span><strong>{summary.soilType}</strong></div>
      <div><span>Farm Size</span><strong>{summary.farmSize}</strong></div>
      <div><span>Current Season</span><strong>{summary.season}</strong></div>
      <div><span>Main Crops</span><strong>{summary.mainCrops || 'No crops selected'}</strong>{!summary.mainCrops && <button className="summary-add-crop" onClick={onAddCrop}>Add crop</button>}</div>
    </div>
  </section>
);

const recommendationSourceLabel = (sources, t) => {
  const values = new Set(sources || []);
  if (values.has('xgboost') && values.has('knowledge_base')) return t('recommendations.sourceCombined');
  if (values.has('xgboost')) return t('recommendations.sourceModel');
  if (values.has('knowledge_base')) return t('recommendations.sourceKnowledge');
  return t('recommendations.sourceLegacy');
};

export const CropRecommendationsGrid = ({ recommendation, refreshing, error, onRefresh }) => {
  const { t } = useTranslation();
  const positiveScoresOnly = (items = []) => items.filter((crop) => {
    const score = crop?.overall_suitability_score;
    return score === null || score === undefined || Number(score) > 0;
  });
  const recommendedCrops = positiveScoresOnly(recommendation?.recommended_crops || []);
  const preliminaryCrops = positiveScoresOnly(recommendation?.preliminary_crops || []);
  const isPreliminary = recommendation?.status === 'preliminary' || (!recommendedCrops.length && preliminaryCrops.length > 0);
  const crops = isPreliminary ? preliminaryCrops : recommendedCrops;
  const quality = recommendation?.data_quality;
  const modelCount = recommendation?.coverage?.model_supported_crop_count;
  const noReliableResult = recommendation?.status === 'no_reliable_recommendation' || (!crops.length && Boolean(recommendation));
  const isTemplateFallback = recommendation?.generation_mode === 'template_fallback';
  const isPartialTemplate = recommendation?.generation_mode === 'partial_template';
  const estimatedSoil = quality?.estimated_features?.some((feature) => ['N', 'P', 'K', 'pH'].includes(feature));
  const measuredSoil = quality?.measured_features?.some((feature) => ['N', 'P', 'K', 'pH'].includes(feature));
  const warningMap = new Map();
  (recommendation?.global_warnings || quality?.warnings || []).forEach((warning, index) => {
    const normalized = typeof warning === 'string' ? { code: `LEGACY_${index}`, message: warning } : warning;
    warningMap.set(normalized.code || normalized.message, normalized);
  });
  const globalWarnings = Array.from(warningMap.values());
  const missingInputs = recommendation?.missing_inputs || [];
  const importantMissingInputs = missingInputs.filter((item) => item.importance === 'high');
  const technicalWarnings = recommendation?.input_snapshot?.model_warnings || [];
  const technicalFeatures = recommendation?.input_snapshot?.model_feature_values || {};
  const technicalContext = recommendation?.input_snapshot?.farm_context || {};
  const canRefresh = importantMissingInputs.length === 0;

  return (
    <section className="panel decision-panel crop-recommendations-panel">
      <div className="panel-header recommendation-header">
        <h2>{t('recommendations.title')}</h2>
        {canRefresh && <button className="recommendation-refresh" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? t('recommendations.generating') : t('recommendations.refresh')}
        </button>}
      </div>

      {typeof modelCount === 'number' && (
        <p className="coverage-note">{t('recommendations.coverage', { count: modelCount })}</p>
      )}
      {recommendation?.is_stale && <div className="recommendation-notice warning">{t('recommendations.stale')}</div>}
      {isTemplateFallback && <div className="recommendation-notice info">{t('recommendations.templateFallback')}</div>}
      {isPartialTemplate && <div className="recommendation-notice info">{t('recommendations.partialTemplate')}</div>}
      {error && <div className="recommendation-notice error">{error}</div>}

      {globalWarnings.length > 0 && (
        <div className="global-warning-panel" data-testid="global-warnings">
          <strong>{t('recommendations.inputLimitations')}</strong>
          <ul>{globalWarnings.map((warning) => <li key={warning.code || warning.message}>{warning.message}</li>)}</ul>
        </div>
      )}

      {importantMissingInputs.length > 0 && (
        <div className="improve-recommendation">
          <div>
            <h3>{t('recommendations.improveTitle')}</h3>
            <p>{t('recommendations.improveCount', { count: importantMissingInputs.length })}</p>
          </div>
          <div className="recommendation-actions">
            {importantMissingInputs.map((item) => (
              <a key={item.field} className="recommendation-action" href={item.action_route}>
                {item.field === 'intended_sowing_date' ? t('recommendations.addSowingDate') : item.field === 'soil_test' ? t('recommendations.addSoilTest') : t('recommendations.reviewRainfall')}
              </a>
            ))}
          </div>
        </div>
      )}

      {isPreliminary && !noReliableResult && (
        <div className="preliminary-heading">
          <h3>{t('recommendations.preliminaryTitle')}</h3>
          <p>{t('recommendations.preliminaryBody')}</p>
        </div>
      )}

      {noReliableResult ? (
        <div className="recommendation-empty">
          <h3>{t('recommendations.noReliableTitle')}</h3>
          <p>{recommendation?.message || recommendation?.disclaimer || t('recommendations.noReliableBody')}</p>
          <div className="recommendation-actions">
            <a className="recommendation-action" href={missingInputs[0]?.action_route || '/questionnaire?refill=1'}>{t('recommendations.completeFarmInfo')}</a>
            {missingInputs.find((item) => item.field === 'soil_test') && <a className="recommendation-action secondary" href={missingInputs.find((item) => item.field === 'soil_test').action_route}>{t('recommendations.addSoilTest')}</a>}
          </div>
        </div>
      ) : (
        <div className="recommendation-cards">
          {crops.map((crop, idx) => {
            const warnings = crop.crop_specific_warnings || crop.warnings || [];
            const reasons = crop.explanation?.why_recommended || crop.matched_conditions || [];
            const nextAction = crop.explanation?.next_actions?.[0];
            const coverage = crop.validation_coverage_summary || {};
            const unavailableChecks = Object.entries(crop.validation_coverage || {})
              .filter(([, value]) => value === 'not_available')
              .map(([key]) => key.replace('_', ' '));
            const candidateStatus = crop.recommendation_status || (isPreliminary ? 'preliminary' : 'recommended');
            return (
              <article key={crop.crop_slug || `${crop.crop_name}-${idx}`} className="recommendation-card">
                <div className="recommendation-card-title">
                  <span className="crop-rank">#{crop.rank || idx + 1}</span>
                  <h4>{crop.crop_name}</h4>
                </div>
                <div className="recommendation-badges">
                  <span className={`suitability-band ${crop.suitability_band || 'insufficient_data'}`}>
                    {candidateStatus === 'preliminary' ? t('recommendations.preliminarySuitability') : t(`recommendations.band.${crop.suitability_band || 'insufficient_data'}`)}
                  </span>
                  <span className={`candidate-status ${candidateStatus}`}>{t(`recommendations.status.${candidateStatus}`)}</span>
                  <span className="source-badge">{recommendationSourceLabel(crop.candidate_sources, t)}</span>
                </div>
                <p className="reliability-line">{t('recommendations.dataReliability')}: {quality?.level || t('recommendations.unknown')}</p>
                <p className="reliability-line">{t('recommendations.soilValues')}: {estimatedSoil ? t('recommendations.estimated') : measuredSoil ? t('recommendations.measured') : t('recommendations.unknown')}</p>
                <div className="validation-summary">
                  <span>{t('recommendations.verifiedMatches')}: {coverage.verified_checks ?? 0}</span>
                  <span>{t('recommendations.unverifiedChecks')}: {coverage.unavailable_checks ?? 8}</span>
                </div>
                {unavailableChecks.length > 0 && <p className="unverified-list">{t('recommendations.couldNotVerify')}: {unavailableChecks.join(', ')}</p>}
                {reasons.length > 0 && (
                  <div className="recommendation-detail">
                    <strong>{t('recommendations.mainReasons')}</strong>
                    <ul>{reasons.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul>
                  </div>
                )}
                {warnings.length > 0 && (
                  <div className="recommendation-detail crop-warnings">
                    <strong>{t('recommendations.warnings')}</strong>
                    <ul>{warnings.slice(0, 3).map((warning) => <li key={warning.code || warning.message || warning}>{warning.message || warning}</li>)}</ul>
                  </div>
                )}
                {nextAction && <p><strong>{t('recommendations.nextAction')}:</strong> {nextAction}</p>}
                {(crop.source_references || []).some((source) => source.url) && (
                  <div className="source-links">
                    {(crop.source_references || []).filter((source) => source.url).map((source) => (
                      <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.name}</a>
                    ))}
                  </div>
                )}
                {!crop.candidate_sources?.length && <p className="legacy-note">{t('recommendations.legacy')}</p>}
              </article>
            );
          })}
          {!crops.length && <div className="recommendation-empty">{t('recommendations.empty')}</div>}
        </div>
      )}

      {recommendation && (
        <details className="technical-details">
          <summary>{t('recommendations.technicalDetails')}</summary>
          <dl>
            <div><dt>{t('recommendations.modelVersion')}</dt><dd>{recommendation.model_version || 'unknown'}</dd></div>
            <div><dt>{t('recommendations.catalogVersion')}</dt><dd>{recommendation.crop_catalog_version || 'unknown'}</dd></div>
            <div><dt>{t('recommendations.generationMode')}</dt><dd>{recommendation.generation_mode || 'unknown'}</dd></div>
            <div><dt>{t('recommendations.modelStatus')}</dt><dd>{recommendation.model_status || 'unknown'}</dd></div>
          </dl>
          {Object.keys(technicalFeatures).length > 0 && (
            <p>
              Model inputs: {Object.entries(technicalFeatures).map(([name, value]) => (
                `${name}=${value === null || value === undefined ? 'not used' : value}`
              )).join(', ')}
            </p>
          )}
          {(technicalContext.temperature_source || technicalContext.humidity_source || technicalContext.rainfall_source) && (
            <p>
              Environmental sources: temperature={technicalContext.temperature_source || 'unknown'}, humidity={technicalContext.humidity_source || 'unknown'}, rainfall={technicalContext.rainfall_source || 'unknown'}
            </p>
          )}
          {crops.map((crop, index) => (
            <p key={crop.crop_slug || `${crop.crop_name || 'legacy-crop'}-${index}`}>{crop.crop_name} — {t('recommendations.productScore')}: {crop.overall_suitability_score ?? 'unknown'}{crop.model_probability !== null && crop.model_probability !== undefined ? `; ${t('recommendations.modelMatch')}: ${Number(crop.model_probability).toFixed(4)}` : ''}</p>
          ))}
          {globalWarnings.length > 0 && <p>Input warning codes: {globalWarnings.map((warning) => warning.code).filter(Boolean).join(', ')}</p>}
          {technicalWarnings.length > 0 && <ul>{technicalWarnings.map((warning, index) => {
            const code = typeof warning === 'string' ? `LEGACY_${index}` : warning.code;
            const message = typeof warning === 'string' ? warning : warning.message;
            return <li key={`${code || 'MODEL_WARNING'}-${index}`}>{code ? `${code}: ` : ''}{message}</li>;
          })}</ul>}
        </details>
      )}
    </section>
  );
};

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
