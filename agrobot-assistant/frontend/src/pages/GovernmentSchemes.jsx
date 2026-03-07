import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Leaf, ArrowLeft, Landmark, RefreshCcw, Loader, Star, Filter } from 'lucide-react';
import ApiService from '../services/api';
import './GovernmentSchemes.css';

const CATEGORY_META = {
  irrigation: { label: 'Irrigation', icon: '💧' },
  plantation: { label: 'Plantation', icon: '🌱' },
  storage: { label: 'Storage', icon: '🏠' },
  equipment: { label: 'Equipment', icon: '🚜' },
  financial: { label: 'Financial Subsidy', icon: '₹' },
  general: { label: 'General', icon: '📄' },
};

const UI_TEXT = {
  en: {
    title: 'Government Schemes',
    subtitle: 'Find useful schemes with subsidy and easy next steps',
    recommended: 'Recommended for Your Farm',
    filters: 'Filters',
    state: 'State',
    crop: 'Crop Type',
    category: 'Category',
    subsidy: 'Subsidy',
    all: 'All',
    actions: {
      details: 'View Details',
      apply: 'Apply Now',
      explain: 'Explain in simple language',
      hide: 'Hide Details',
    },
    labels: {
      estimated: 'Estimated Benefit',
      docs: 'Documents Required',
      difficulty: 'Difficulty',
      time: 'Estimated approval time',
      officialLinks: 'Official Government Links',
      schemePdf: 'Scheme PDF',
      myScheme: 'Apply on myScheme Portal',
      dept: 'Department of Agriculture',
    },
    loading: 'Fetching latest schemes...',
    refresh: 'Refresh',
    back: 'Back to Dashboard',
    noData: 'No scheme details available for current filters.',
  },
  hi: {
    title: 'सरकारी योजनाएं',
    subtitle: 'सब्सिडी और आसान अगला कदम के साथ उपयोगी योजनाएं देखें',
    recommended: 'आपके खेत के लिए सुझाई गई योजनाएं',
    filters: 'फ़िल्टर',
    state: 'राज्य',
    crop: 'फसल प्रकार',
    category: 'श्रेणी',
    subsidy: 'सब्सिडी',
    all: 'सभी',
    actions: {
      details: 'विवरण देखें',
      apply: 'अभी आवेदन करें',
      explain: 'सरल भाषा में समझाएं',
      hide: 'विवरण छुपाएं',
    },
    labels: {
      estimated: 'अनुमानित लाभ',
      docs: 'ज़रूरी दस्तावेज़',
      difficulty: 'कठिनाई स्तर',
      time: 'अनुमानित स्वीकृति समय',
      officialLinks: 'आधिकारिक सरकारी लिंक',
      schemePdf: 'योजना PDF',
      myScheme: 'myScheme पोर्टल पर आवेदन',
      dept: 'कृषि विभाग',
    },
    loading: 'नवीनतम योजनाएं प्राप्त की जा रही हैं...',
    refresh: 'रीफ्रेश',
    back: 'डैशबोर्ड पर वापस जाएं',
    noData: 'इन फ़िल्टरों के लिए योजना उपलब्ध नहीं है।',
  },
};

const GovernmentSchemes = () => {
  const [schemes, setSchemes] = useState(null);
  const [expandedSchemes, setExpandedSchemes] = useState([]);
  const [language, setLanguage] = useState('en');
  const [selectedState, setSelectedState] = useState('all');
  const [cropType, setCropType] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [subsidyFilter, setSubsidyFilter] = useState('all');
  const [quickTypeFilter, setQuickTypeFilter] = useState('all');
  const [aiExplanations, setAiExplanations] = useState({});
  const [aiLoadingIndex, setAiLoadingIndex] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const t = UI_TEXT[language];

  const parseSubsidy = (scheme) => {
    const text = `${scheme.brief_description || ''} ${scheme.eligibility || ''} ${scheme.how_to_apply || ''}`;
    const match = text.match(/(\d{1,2})\s*%/);
    return match ? Number(match[1]) : null;
  };

  const inferCategory = (scheme) => {
    const text = `${scheme.name || ''} ${scheme.brief_description || ''}`.toLowerCase();
    if (/irrigation|drip|sprinkler|water/.test(text)) return 'irrigation';
    if (/plant|horticulture|orchard|nursery|seedling/.test(text)) return 'plantation';
    if (/storage|warehouse|cold storage|godown/.test(text)) return 'storage';
    if (/tractor|implement|equipment|machinery|farm tool/.test(text)) return 'equipment';
    if (/subsidy|financial|loan|credit|pm-kisan|insurance/.test(text)) return 'financial';
    return 'general';
  };

  const subsidyBand = (subsidy) => {
    if (typeof subsidy !== 'number') return 'info';
    if (subsidy > 40) return 'high';
    if (subsidy >= 20) return 'medium';
    return 'info';
  };

  const inferDifficulty = (scheme) => {
    const text = `${scheme.eligibility || ''} ${scheme.how_to_apply || ''}`.toLowerCase();
    if (/online|portal|single window|self apply/.test(text)) return 'Easy';
    if (/document|verification|office|district/.test(text)) return 'Medium';
    return 'Complex';
  };

  const inferApprovalTime = (difficulty) => {
    if (difficulty === 'Easy') return '15-30 days';
    if (difficulty === 'Medium') return '30-60 days';
    return '45-90 days';
  };

  const inferDocuments = (scheme) => {
    const text = `${scheme.eligibility || ''} ${scheme.how_to_apply || ''}`.toLowerCase();
    const docs = ['Aadhaar', 'Bank Passbook'];
    if (/land|farmer|khasra|khatauni/.test(text)) docs.push('Land Record');
    if (/income|certificate/.test(text)) docs.push('Income Certificate');
    return docs.slice(0, 4).join(', ');
  };

  const inferStateFromText = (scheme) => {
    const text = `${scheme.name || ''} ${scheme.brief_description || ''} ${scheme.eligibility || ''}`.toLowerCase();
    const states = ['Madhya Pradesh', 'Maharashtra', 'Uttar Pradesh', 'Punjab', 'Rajasthan', 'Gujarat', 'Karnataka', 'Tamil Nadu'];
    const match = states.find((state) => text.includes(state.toLowerCase()));
    return match || 'India';
  };

  const calculateEstimatedBenefit = (subsidy) => {
    if (typeof subsidy !== 'number') return 15000;
    return Math.max(12000, Math.round((subsidy / 100) * 60000));
  };

  const normalizeScheme = (scheme, index, sourceUrl) => {
    const subsidy = parseSubsidy(scheme);
    const category = inferCategory(scheme);
    const difficulty = inferDifficulty(scheme);
    const state = inferStateFromText(scheme);
    return {
      id: `${index}-${scheme.name}`,
      name: scheme.name,
      shortDescription: scheme.brief_description || 'Official scheme support for eligible farmers.',
      eligibility: scheme.eligibility || 'Please check official criteria before applying.',
      applyInfo: scheme.how_to_apply || sourceUrl || 'Visit official portal to apply.',
      subsidy,
      subsidyBand: subsidyBand(subsidy),
      category,
      estimatedBenefit: calculateEstimatedBenefit(subsidy),
      documentsRequired: inferDocuments(scheme),
      difficulty,
      approvalTime: inferApprovalTime(difficulty),
      state,
      sourceUrl,
    };
  };

  const buildSimpleExplanation = (scheme) => {
    if (language === 'hi') {
      return `${scheme.name} योजना में ${scheme.subsidy ? `${scheme.subsidy}%` : 'उपलब्ध'} सहायता मिल सकती है। यह ${CATEGORY_META[scheme.category].label} श्रेणी की योजना है। आवेदन के लिए ${scheme.documentsRequired} जैसे दस्तावेज़ तैयार रखें और समय पर पोर्टल/विभाग में आवेदन करें।`;
    }
    return `${scheme.name} can provide ${scheme.subsidy ? `${scheme.subsidy}%` : 'available'} support for your farm. It belongs to the ${CATEGORY_META[scheme.category].label} category. Keep documents like ${scheme.documentsRequired} ready and apply through the official portal/department.`;
  };

  const loadSchemes = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await ApiService.getGovernmentSchemes();
      setSchemes(response);
      setExpandedSchemes([]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load government schemes.');
      setSchemes(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchemes();
  }, []);

  const schemeCards = useMemo(() => {
    const sourceMap = (schemes?.sources || []).reduce((acc, src) => {
      const key = (src.title || '').toLowerCase();
      if (key && !acc[key]) acc[key] = src.url;
      return acc;
    }, {});

    const rawSchemes = Array.isArray(schemes?.schemes) ? schemes.schemes : [];
    return rawSchemes.map((scheme, index) => {
      const sourceUrl = sourceMap[(scheme.name || '').toLowerCase()] || (schemes?.sources?.[0]?.url || '');
      return normalizeScheme(scheme, index, sourceUrl);
    });
  }, [schemes]);

  const orderedSources = useMemo(() => {
    return (schemes?.sources || [])
      .filter((src) => src?.url)
      .slice()
      .sort((a, b) => (a.title || '').localeCompare(b.title || ''));
  }, [schemes]);

  const stateOptions = useMemo(() => {
    const uniqueStates = [...new Set(schemeCards.map((scheme) => scheme.state).filter(Boolean))];
    return ['all', ...uniqueStates];
  }, [schemeCards]);

  const filteredSchemes = useMemo(() => {
    return schemeCards.filter((scheme) => {
      if (selectedState !== 'all' && scheme.state !== selectedState) return false;
      if (categoryFilter !== 'all' && scheme.category !== categoryFilter) return false;
      if (quickTypeFilter !== 'all' && scheme.category !== quickTypeFilter) return false;
      if (cropType.trim()) {
        const haystack = `${scheme.name} ${scheme.shortDescription} ${scheme.eligibility}`.toLowerCase();
        if (!haystack.includes(cropType.trim().toLowerCase())) return false;
      }
      if (subsidyFilter === 'high' && !(typeof scheme.subsidy === 'number' && scheme.subsidy > 40)) return false;
      if (subsidyFilter === 'medium' && !(typeof scheme.subsidy === 'number' && scheme.subsidy >= 20 && scheme.subsidy <= 40)) return false;
      if (subsidyFilter === 'info' && typeof scheme.subsidy === 'number') return false;
      return true;
    });
  }, [schemeCards, selectedState, categoryFilter, quickTypeFilter, cropType, subsidyFilter]);

  const recommendedSchemes = useMemo(() => {
    const scored = [...filteredSchemes].map((scheme) => {
      let score = 0;
      if (scheme.subsidyBand === 'high') score += 3;
      if (scheme.subsidyBand === 'medium') score += 2;
      if (scheme.difficulty === 'Easy') score += 2;
      if (scheme.category === 'irrigation' || scheme.category === 'equipment') score += 1;
      return { ...scheme, score };
    });
    return scored.sort((a, b) => b.score - a.score).slice(0, 3);
  }, [filteredSchemes]);

  const toggleScheme = (idx) => {
    setExpandedSchemes((prev) =>
      prev.includes(idx) ? prev.filter((item) => item !== idx) : [...prev, idx]
    );
  };

  const handleExplain = async (scheme) => {
    setAiLoadingIndex(scheme.id);
    await new Promise((resolve) => setTimeout(resolve, 350));
    setAiExplanations((prev) => ({
      ...prev,
      [scheme.id]: buildSimpleExplanation(scheme),
    }));
    setAiLoadingIndex(null);
  };

  const getApplyLink = (scheme) => {
    if (/https?:\/\//i.test(scheme.applyInfo)) return scheme.applyInfo;
    if (scheme.sourceUrl) return scheme.sourceUrl;
    return 'https://www.myscheme.gov.in/';
  };

  const renderSchemeCard = (scheme, idx, featured = false) => {
    const subsidyText = typeof scheme.subsidy === 'number' ? `${scheme.subsidy}% subsidy` : 'Info scheme';
    const badgeClass = `subsidy-badge ${scheme.subsidyBand}`;
    const categoryMeta = CATEGORY_META[scheme.category] || CATEGORY_META.general;
    const expanded = expandedSchemes.includes(scheme.id);
    const explainText = aiExplanations[scheme.id];

    return (
      <article className={`scheme-card-v2 ${featured ? 'featured' : ''}`} key={`${scheme.id}-${idx}`}>
        <div className="scheme-card-top">
          <div className="scheme-category-pill">
            <span className="scheme-category-icon" aria-hidden="true">{categoryMeta.icon}</span>
            <span>{categoryMeta.label}</span>
          </div>
          <span className={badgeClass}>{subsidyText}</span>
        </div>

        <h3>{scheme.name}</h3>
        <p className="scheme-desc">{scheme.shortDescription}</p>

        <div className="scheme-estimate">
          <span>{t.labels.estimated}</span>
          <strong>₹{scheme.estimatedBenefit.toLocaleString('en-IN')}</strong>
        </div>

        <div className="scheme-quick-meta">
          <div><strong>{t.labels.docs}:</strong> {scheme.documentsRequired}</div>
          <div><strong>{t.labels.difficulty}:</strong> {scheme.difficulty}</div>
          <div><strong>{t.labels.time}:</strong> {scheme.approvalTime}</div>
        </div>

        {expanded && (
          <div className="scheme-extra-details">
            <p><strong>Eligibility:</strong> {scheme.eligibility}</p>
            <p><strong>How to apply:</strong> {scheme.applyInfo}</p>
          </div>
        )}

        {explainText && <div className="scheme-ai-note">🤖 {explainText}</div>}

        <div className="scheme-actions">
          <button className="btn-ghost" onClick={() => toggleScheme(scheme.id)}>
            {expanded ? t.actions.hide : t.actions.details}
          </button>
          <a className="btn-primary" href={getApplyLink(scheme)} target="_blank" rel="noreferrer">
            {t.actions.apply}
          </a>
          <button
            className="btn-outline"
            onClick={() => handleExplain(scheme)}
            disabled={aiLoadingIndex === scheme.id}
          >
            {aiLoadingIndex === scheme.id ? '...' : t.actions.explain}
          </button>
        </div>
      </article>
    );
  };

  return (
    <div className="government-schemes-page">
      <header className="government-schemes-header">
        <div className="government-schemes-logo">
          <Leaf className="government-schemes-logo-icon" />
          <span>AgroBot</span>
        </div>
        <div className="government-schemes-header-actions">
          <div className="language-toggle" role="group" aria-label="Language selector">
            <button
              className={language === 'en' ? 'active' : ''}
              onClick={() => setLanguage('en')}
            >
              English
            </button>
            <button
              className={language === 'hi' ? 'active' : ''}
              onClick={() => setLanguage('hi')}
            >
              हिंदी
            </button>
          </div>
          <button className="government-schemes-refresh" onClick={loadSchemes} disabled={loading}>
            {loading ? <Loader size={14} className="government-schemes-spin" /> : <RefreshCcw size={14} />}
            {t.refresh}
          </button>
          <Link to="/dashboard" className="government-schemes-back-link">
            <ArrowLeft size={16} />
            {t.back}
          </Link>
        </div>
      </header>

      <main className="government-schemes-main">
        <section className="government-schemes-card">
          <div className="government-schemes-title-wrap">
            <Landmark size={20} />
            <div>
              <h1>{t.title}</h1>
              <p>{t.subtitle}</p>
            </div>
          </div>

          <section className="filters-panel">
            <div className="filters-title">
              <Filter size={16} />
              <span>{t.filters}</span>
            </div>
            <div className="filters-grid">
              <label>
                <span>{t.state}</span>
                <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)}>
                  {stateOptions.map((option) => (
                    <option value={option} key={option}>{option === 'all' ? t.all : option}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t.crop}</span>
                <input
                  type="text"
                  value={cropType}
                  onChange={(e) => setCropType(e.target.value)}
                  placeholder={language === 'hi' ? 'जैसे धान, गेहूं' : 'e.g. wheat, paddy'}
                />
              </label>
              <label>
                <span>{t.category}</span>
                <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                  <option value="all">{t.all}</option>
                  <option value="irrigation">Irrigation</option>
                  <option value="plantation">Plantation</option>
                  <option value="storage">Storage</option>
                  <option value="equipment">Equipment</option>
                  <option value="financial">Financial</option>
                </select>
              </label>
              <label>
                <span>{t.subsidy}</span>
                <select value={subsidyFilter} onChange={(e) => setSubsidyFilter(e.target.value)}>
                  <option value="all">{t.all}</option>
                  <option value="high">&gt; 40%</option>
                  <option value="medium">20% - 40%</option>
                  <option value="info">Informational</option>
                </select>
              </label>
            </div>
            <div className="quick-type-chips">
              {['all', 'equipment', 'irrigation', 'storage'].map((chip) => (
                <button
                  key={chip}
                  className={quickTypeFilter === chip ? 'chip active' : 'chip'}
                  onClick={() => setQuickTypeFilter(chip)}
                >
                  {chip === 'all' ? t.all : chip[0].toUpperCase() + chip.slice(1)}
                </button>
              ))}
            </div>
          </section>

          {error && <div className="government-schemes-error">{error}</div>}

          {loading ? (
            <div className="government-schemes-loading">
              <Loader className="government-schemes-spin" size={22} />
              <span>{t.loading}</span>
            </div>
          ) : (
            <>
              <section className="recommended-section">
                <h2>{t.recommended} <Star size={16} className="star-inline" /></h2>
                <div className="recommended-grid">
                  {recommendedSchemes.map((scheme, idx) => (
                    <div className="recommended-item" key={scheme.id}>
                      <span className="recommended-rank">⭐ Top {idx + 1}</span>
                      {renderSchemeCard(scheme, idx, true)}
                    </div>
                  ))}
                </div>
              </section>

              <section className="scheme-grid-section">
                <div className="scheme-grid">
                  {filteredSchemes.map((scheme, idx) => renderSchemeCard(scheme, idx))}
                </div>
                {filteredSchemes.length === 0 && (
                  <div className="schemes-empty">{t.noData}</div>
                )}
              </section>

              <section className="official-links-section">
                <h3>{t.labels.officialLinks}</h3>
                <div className="official-links-list">
                  <a href={orderedSources[0]?.url || 'https://www.india.gov.in/topics/agriculture'} target="_blank" rel="noreferrer">
                    📄 {t.labels.schemePdf}
                  </a>
                  <a href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer">
                    🔗 {t.labels.myScheme}
                  </a>
                  <a href="https://agricoop.nic.in/" target="_blank" rel="noreferrer">
                    🏛 {t.labels.dept}
                  </a>
                  {orderedSources.slice(0, 5).map((src, idx) => (
                    <a href={src.url} target="_blank" rel="noreferrer" key={idx}>
                      📄 {src.title || src.url}
                    </a>
                  ))}
                </div>
              </section>
            </>
          )}
        </section>
      </main>
    </div>
  );
};

export default GovernmentSchemes;
