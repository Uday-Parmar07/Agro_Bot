import React from 'react';
import { Home, Sprout, CloudSun, BarChart3, RefreshCcw, Landmark, Settings, Bell, Plus, CloudRain, Droplets, Wind, Thermometer, MessageCircle, UserCheck, IndianRupee, ChevronDown, LogOut, MoreHorizontal, X, Camera, HelpCircle, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/* Lucide at stroke-width 2.75 — the Organic system's rounder, heavier icon weight. */
const ICON = { strokeWidth: 2.75 };

const priorityClass = (priority) => {
  const value = String(priority || '').toLowerCase();
  if (value === 'high' || value === 'urgent') return 'priority urgent';
  if (value === 'medium') return 'priority warning';
  return 'priority good';
};

/* The nav is declared once and consumed by the sidebar, the bottom tab bar and
   the More sheet, so a phone can reach every destination the desktop can. */
export const NAV_ITEMS = [
  { key: 'dashboard', labelKey: 'nav.dashboard', Icon: Home, tab: true },
  { key: 'crops', labelKey: 'nav.crops', Icon: Sprout, tab: true },
  { key: 'weather', labelKey: 'nav.weather', Icon: CloudSun },
  { key: 'insights', labelKey: 'nav.insights', Icon: BarChart3 },
  { key: 'analytics', labelKey: 'nav.analytics', Icon: BarChart3, href: '/analytics' },
  { key: 'disease', labelKey: 'nav.disease', Icon: Camera, href: '/disease-checkup', tab: true },
  { key: 'questionnaire', labelKey: 'nav.questionnaire', Icon: RefreshCcw, href: '/questionnaire?refill=1' },
  { key: 'schemes', labelKey: 'nav.schemes', Icon: Landmark, href: '/government-schemes' },
  { key: 'mandi', labelKey: 'nav.mandiPrices', Icon: IndianRupee, href: '/mandi-prices', tab: true },
  { key: 'advisor', labelKey: 'nav.advisor', Icon: UserCheck, href: '/advisor', roles: ['advisor', 'admin'] },
  { key: 'settings', labelKey: 'nav.settings', Icon: Settings },
];

const visibleNav = (role) => NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(role));

const hrefFor = (item, farmId) => (
  item.key === 'questionnaire' && farmId ? `${item.href}&farm_id=${farmId}` : item.href
);

export const DecisionSidebar = ({ user, activeTab, setActiveTab, logout, onAddCrop, farmId, farmLabel, onNavigate }) => {
  const { t } = useTranslation();

  const handle = (item) => {
    if (item.href) {
      onNavigate(hrefFor(item, farmId));
      return;
    }
    setActiveTab(item.key);
  };

  return (
    <aside className="sidebar" aria-label="App navigation">
      <div className="sidebar-header">
        <span className="logo">
          <Sprout className="logo-icon" {...ICON} />
          <span className="logo-text">AgroBot</span>
        </span>
      </div>

      {farmLabel && (
        <button type="button" className="farm-switcher" onClick={() => setActiveTab('settings')}>
          <span style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
            <span style={{ display: 'block', fontWeight: 700, fontSize: 15 }}>{farmLabel.name}</span>
            <span style={{ display: 'block', fontSize: 13, color: 'var(--ink-muted)' }}>{farmLabel.detail}</span>
          </span>
          <ChevronDown size={18} {...ICON} />
        </button>
      )}

      <nav className="sidebar-nav" aria-label="Main">
        {visibleNav(user?.role).map((item) => {
          const active = !item.href && activeTab === item.key;
          return (
            <button
              key={item.key}
              type="button"
              className={`nav-item ${active ? 'active' : ''}`}
              aria-current={active ? 'page' : undefined}
              onClick={() => handle(item)}
            >
              <item.Icon size={18} {...ICON} />
              <span>{t(item.labelKey)}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-quick-actions">
        <h4>Quick actions</h4>
        <button type="button" className="sidebar-action-btn" onClick={onAddCrop}>
          <Plus size={16} {...ICON} /> Add crop
        </button>
        <button type="button" className="sidebar-action-btn" onClick={() => onNavigate('/disease-checkup')}>
          <Camera size={16} {...ICON} /> Check a leaf
        </button>
        <button type="button" className="sidebar-action-btn" onClick={() => setActiveTab('weather')}>
          <CloudSun size={16} {...ICON} /> Weather
        </button>
        <button type="button" className="sidebar-action-btn" onClick={() => setActiveTab('insights')}>
          <Droplets size={16} {...ICON} /> Irrigation advice
        </button>
      </div>

      <div className="sidebar-footer">
        <div className="user-info">
          <span className="user-name">{user?.full_name}</span>
          <span className="user-email">{user?.email}</span>
        </div>
        <button type="button" onClick={logout} className="logout-btn">
          <LogOut size={16} {...ICON} /> {t('nav.logout')}
        </button>
      </div>
    </aside>
  );
};

export const AppTopBar = ({ farmLabel, onAsk }) => (
  <header className="app-topbar">
    <Sprout className="app-topbar-brand" {...ICON} />
    <div className="app-topbar-farm">
      <strong>{farmLabel?.name || 'AgroBot'}</strong>
      <span>{farmLabel?.detail || 'Your farm at a glance'}</span>
    </div>
    <button type="button" className="btn btn-secondary" onClick={onAsk}>
      <MessageCircle size={16} {...ICON} /> Ask
    </button>
  </header>
);

/* Four destinations plus More. Nothing in the sidebar becomes unreachable. */
export const MobileTabBar = ({ user, activeTab, setActiveTab, farmId, onNavigate, onMore, moreOpen }) => {
  const { t } = useTranslation();
  const tabs = visibleNav(user?.role).filter((item) => item.tab);
  const tabKeys = tabs.map((item) => item.key);
  const moreActive = moreOpen || !tabKeys.includes(activeTab);

  return (
    <nav className="app-tabbar" aria-label="Main">
      {tabs.map((item) => {
        const active = !item.href && activeTab === item.key;
        return (
          <button
            key={item.key}
            type="button"
            className={`app-tab ${active ? 'active' : ''}`}
            aria-current={active ? 'page' : undefined}
            onClick={() => (item.href ? onNavigate(hrefFor(item, farmId)) : setActiveTab(item.key))}
          >
            <span className="app-tab-icon"><item.Icon size={20} {...ICON} /></span>
            {t(item.labelKey)}
          </button>
        );
      })}
      <button
        type="button"
        className={`app-tab ${moreActive ? 'active' : ''}`}
        aria-expanded={moreOpen}
        onClick={onMore}
      >
        <span className="app-tab-icon"><MoreHorizontal size={20} {...ICON} /></span>
        More
      </button>
    </nav>
  );
};

export const MoreSheet = ({ user, activeTab, setActiveTab, farmId, onNavigate, onClose, logout }) => {
  const { t } = useTranslation();

  return (
    <div className="dialog-backdrop sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="More" onClick={(event) => event.stopPropagation()}>
        <div className="more-sheet-head">
          <p>More</p>
          <button type="button" className="btn btn-secondary btn-icon" aria-label="Close" onClick={onClose}>
            <X size={18} {...ICON} />
          </button>
        </div>
        {visibleNav(user?.role).map((item) => {
          const active = !item.href && activeTab === item.key;
          return (
            <button
              key={item.key}
              type="button"
              className={`more-sheet-item ${active ? 'active' : ''}`}
              onClick={() => {
                if (item.href) onNavigate(hrefFor(item, farmId));
                else setActiveTab(item.key);
                onClose();
              }}
            >
              <item.Icon size={20} {...ICON} />
              {t(item.labelKey)}
            </button>
          );
        })}
        <button type="button" className="more-sheet-item danger" onClick={logout}>
          <LogOut size={20} {...ICON} /> {t('nav.logout')}
        </button>
      </div>
    </div>
  );
};

export const TodayOnFarm = ({ items }) => (
  <section className="panel decision-panel today-panel" aria-labelledby="today-h">
    <div className="panel-header"><h2 id="today-h">Today on Your Farm</h2></div>
    <ul className="today-list">
      {items.map((item, idx) => (
        <li key={idx} className="today-item">
          <span className="today-item-icon" aria-hidden="true">{item.icon}</span>
          <div className="today-item-body">
            <strong>{item.title}</strong>
            <p>{item.note}</p>
          </div>
        </li>
      ))}
    </ul>
  </section>
);

export const StatusCards = ({ score, soilStatus, alertCount, taskCount, assessmentRoute }) => {
  const scoreTone = score === null ? 'none' : score >= 7 ? 'good' : score >= 5 ? 'caution' : 'urgent';
  const soilTone = soilStatus.toLowerCase().includes('good')
    ? 'good'
    : soilStatus.toLowerCase().includes('not assessed') ? 'none' : 'caution';

  const cards = [
    {
      title: 'Farm Health Score',
      value: score === null ? '—' : score.toFixed(1),
      unit: score === null ? null : ' / 10',
      tone: scoreTone,
      pill: score === null ? 'Not assessed' : soilStatus,
    },
    { title: 'Soil Health Status', value: soilStatus, tone: soilTone, pill: null, text: true },
    {
      title: 'Alerts / Warnings',
      value: String(alertCount),
      tone: alertCount > 0 ? 'caution' : 'good',
      pill: alertCount > 0 ? 'Needs attention' : 'All clear',
    },
    {
      title: "Today's Tasks",
      value: String(taskCount),
      tone: taskCount > 2 ? 'caution' : 'good',
      pill: null,
    },
  ];

  return (
    <section className="status-section">
      <div className="status-grid">
        {cards.map((card, idx) => (
          <article key={idx} className={`status-card ${card.tone}`}>
            <h4>{card.title}</h4>
            <strong style={card.text ? { fontSize: 24 } : undefined}>
              {card.value}
              {card.unit && <span style={{ fontSize: 20 }}>{card.unit}</span>}
            </strong>
            {card.pill && (
              <span className={`status-pill ${card.tone}`}>
                {card.tone === 'none' ? <HelpCircle size={14} {...ICON} />
                  : card.tone === 'good' ? <CheckCircle2 size={14} {...ICON} />
                    : <AlertTriangle size={14} {...ICON} />}
                {card.pill}
              </span>
            )}
          </article>
        ))}
      </div>
      {score === null && (
        <div className="assessment-empty">
          <div>
            <strong>Farm health not assessed</strong>
            <p>Complete farm details or add a soil test to generate an assessment.</p>
          </div>
          <a className="recommendation-action" href={assessmentRoute}>Complete assessment</a>
        </div>
      )}
    </section>
  );
};

export const AlertsPanel = ({ alerts }) => (
  <section className="panel decision-panel">
    <div className="panel-header"><h2><Bell size={18} {...ICON} /> Alerts</h2></div>
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
        <div><Thermometer size={16} {...ICON} /> {weather.temperature === null ? 'Unavailable' : `${Math.round(weather.temperature)}°C`}</div>
        <div><CloudRain size={16} {...ICON} /> Rain {weather.rainProbability === null ? 'Unavailable' : `${Math.round(weather.rainProbability)}%`}</div>
        <div><Wind size={16} {...ICON} /> {weather.windSpeed === null ? 'Unavailable' : `${Math.round(weather.windSpeed)} km/h`}</div>
        <div><Droplets size={16} {...ICON} /> {weather.humidity === null ? 'Unavailable' : `${Math.round(weather.humidity)}%`}</div>
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
        <div>
          <h2>{t('recommendations.title')}</h2>
          {typeof modelCount === 'number' && (
            <p className="coverage-note">{t('recommendations.coverage', { count: modelCount })}</p>
          )}
        </div>
        {canRefresh && <button className="recommendation-refresh" onClick={onRefresh} disabled={refreshing}>
          <RefreshCcw size={14} {...ICON} />
          {refreshing ? t('recommendations.generating') : t('recommendations.refresh')}
        </button>}
      </div>

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
                  <span className="crop-rank">{crop.rank || idx + 1}</span>
                  <h4>{crop.crop_name}</h4>
                </div>
                <div className="recommendation-badges">
                  <span className={`suitability-band ${crop.suitability_band || 'insufficient_data'}`}>
                    {candidateStatus === 'preliminary' ? t('recommendations.preliminarySuitability') : t(`recommendations.band.${crop.suitability_band || 'insufficient_data'}`)}
                  </span>
                  <span className={`candidate-status ${candidateStatus}`}>{t(`recommendations.status.${candidateStatus}`)}</span>
                  <span className="source-badge">{recommendationSourceLabel(crop.candidate_sources, t)}</span>
                </div>
                {nextAction && <p><strong>{t('recommendations.nextAction')}:</strong> {nextAction}</p>}
                <div className="validation-summary">
                  <span>{t('recommendations.verifiedMatches')}: {coverage.verified_checks ?? 0}</span>
                  <span>{t('recommendations.unverifiedChecks')}: {coverage.unavailable_checks ?? 8}</span>
                </div>
                {unavailableChecks.length > 0 && <p className="unverified-list">{t('recommendations.couldNotVerify')}: {unavailableChecks.join(', ')}</p>}
                {(reasons.length > 0 || warnings.length > 0) && (
                  <details className="recommendation-detail">
                    <summary style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: 44, fontWeight: 700, color: 'var(--color-accent-700)' }}>
                      {t('recommendations.mainReasons')}
                      <ChevronDown size={18} className="chev" {...ICON} />
                    </summary>
                    {reasons.length > 0 && (
                      <ul>{reasons.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul>
                    )}
                    {warnings.length > 0 && (
                      <ul className="crop-warnings">{warnings.slice(0, 3).map((warning) => <li key={warning.code || warning.message || warning}>{warning.message || warning}</li>)}</ul>
                    )}
                    <p className="reliability-line">{t('recommendations.dataReliability')}: {quality?.level || t('recommendations.unknown')} · {t('recommendations.soilValues')}: {estimatedSoil ? t('recommendations.estimated') : measuredSoil ? t('recommendations.measured') : t('recommendations.unknown')}</p>
                  </details>
                )}
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
          <summary>{t('recommendations.technicalDetails')}<ChevronDown size={16} className="chev" {...ICON} /></summary>
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
          <div className="task-left">
            <span className="task-icon" aria-hidden="true">{task.icon}</span>
            <div><strong>{task.dateLabel} — {task.activity}</strong><p>{task.description}</p></div>
          </div>
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

export const AskAgroBotDialog = ({ onClose }) => {
  const [answer, setAnswer] = React.useState(null);
  const prompts = [
    'When should I irrigate my field?',
    'Which crop suits my soil?',
    'How to treat this disease?',
  ];

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="ask-h" onClick={(event) => event.stopPropagation()}>
        <div className="dialog-head">
          <h2 id="ask-h" className="dialog-title">Ask AgroBot</h2>
          <button type="button" className="btn btn-secondary btn-icon" aria-label="Close" onClick={onClose}>
            <X size={18} {...ICON} />
          </button>
        </div>
        <p className="dialog-body">Quick help for daily decisions. Ask in English or हिंदी.</p>
        <div className="assistant-prompt-list">
          {prompts.map((prompt) => (
            <button key={prompt} type="button" onClick={() => setAnswer(`AgroBot can't answer "${prompt}" yet — the assistant is not connected in this build.`)}>
              {prompt}
            </button>
          ))}
        </div>
        {answer && <p className="assistant-answer" aria-live="polite">{answer}</p>}
      </div>
    </div>
  );
};
