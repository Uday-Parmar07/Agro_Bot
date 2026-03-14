import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Leaf, ArrowLeft, Landmark, Loader, Search, X, Clock,
  FileText, CheckCircle2, AlertTriangle, ChevronRight, RefreshCcw,
  Sparkles, ShieldCheck, ExternalLink,
} from 'lucide-react';
import ApiService from '../services/api';
import './GovernmentSchemes.css';

/* ── i18n ───────────────────────────────────────────────── */
const CATEGORY_META = {
  irrigation:  { label: 'Irrigation',  labelHi: 'सिंचाई',       icon: '💧' },
  plantation:  { label: 'Plantation',  labelHi: 'रोपण',         icon: '🌱' },
  storage:     { label: 'Storage',     labelHi: 'भंडारण',       icon: '🏠' },
  equipment:   { label: 'Equipment',   labelHi: 'उपकरण',        icon: '🚜' },
  financial:   { label: 'Financial',   labelHi: 'वित्तीय सहायता', icon: '₹' },
  general:     { label: 'General',     labelHi: 'सामान्य',       icon: '📄' },
};

const INDIAN_STATES = [
  'Andhra Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana',
  'Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh',
  'Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab',
  'Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh',
  'Uttarakhand','West Bengal',
];

const T = {
  en: {
    title: 'Government Schemes',
    subtitle: 'Find the best schemes for your farm in 3 easy steps',
    step1: 'Your Farm Profile',
    step2: 'Best Schemes for You',
    step3: 'Scheme Details',
    state: 'State',
    crop: 'Crop',
    farmSize: 'Farm Size',
    small: 'Small',
    medium: 'Medium',
    large: 'Large',
    findSchemes: 'Find Best Schemes',
    loading: 'Searching government schemes...',
    back: 'Dashboard',
    recommended: 'AI Recommended',
    match: 'match',
    benefit: 'Estimated Benefit',
    difficulty: 'Difficulty',
    approval: 'Approval Time',
    docs: 'Required Documents',
    eligibility: 'Eligibility',
    howToApply: 'How to Apply',
    apply: 'Apply on Official Portal',
    prepareDocs: 'Prepare Documents',
    explain: 'Explain Simply',
    whyRecommended: 'Why recommended?',
    noSchemes: 'No schemes found. Try adjusting your profile.',
    retry: 'Retry',
    errorText: 'Something went wrong. Please try again.',
    officialLinks: 'Official Government Links',
    selectState: 'Select your state',
    cropPlaceholder: 'e.g. wheat, rice, cotton',
    close: 'Close',
    schemePdf: 'Scheme PDF',
    myScheme: 'myScheme Portal',
    dept: 'Dept. of Agriculture',
    docsChecklist: 'Documents Checklist',
    subsidyLabel: 'subsidy',
    infoScheme: 'Info',
    easy: 'Easy', med: 'Medium', hard: 'Complex',
    days: 'days',
  },
  hi: {
    title: 'सरकारी योजनाएं',
    subtitle: '3 आसान चरणों में अपने खेत के लिए सबसे अच्छी योजनाएं खोजें',
    step1: 'आपकी खेत प्रोफ़ाइल',
    step2: 'आपके लिए सबसे अच्छी योजनाएं',
    step3: 'योजना विवरण',
    state: 'राज्य',
    crop: 'फसल',
    farmSize: 'खेत का आकार',
    small: 'छोटा',
    medium: 'मध्यम',
    large: 'बड़ा',
    findSchemes: 'सबसे अच्छी योजनाएं खोजें',
    loading: 'सरकारी योजनाएं खोजी जा रही हैं...',
    back: 'डैशबोर्ड',
    recommended: 'AI अनुशंसित',
    match: 'मिलान',
    benefit: 'अनुमानित लाभ',
    difficulty: 'कठिनाई',
    approval: 'स्वीकृति समय',
    docs: 'आवश्यक दस्तावेज़',
    eligibility: 'पात्रता',
    howToApply: 'कैसे आवेदन करें',
    apply: 'आधिकारिक पोर्टल पर आवेदन करें',
    prepareDocs: 'दस्तावेज़ तैयार करें',
    explain: 'सरल भाषा में समझाएं',
    whyRecommended: 'क्यों अनुशंसित?',
    noSchemes: 'कोई योजना नहीं मिली। अपनी प्रोफ़ाइल बदलकर देखें।',
    retry: 'पुनः प्रयास',
    errorText: 'कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।',
    officialLinks: 'आधिकारिक सरकारी लिंक',
    selectState: 'अपना राज्य चुनें',
    cropPlaceholder: 'जैसे गेहूं, धान, कपास',
    close: 'बंद करें',
    schemePdf: 'योजना PDF',
    myScheme: 'myScheme पोर्टल',
    dept: 'कृषि विभाग',
    docsChecklist: 'दस्तावेज़ चेकलिस्ट',
    subsidyLabel: 'सब्सिडी',
    infoScheme: 'जानकारी',
    easy: 'आसान', med: 'मध्यम', hard: 'कठिन',
    days: 'दिन',
  },
};

/* ── helpers ─────────────────────────────────────────────── */
const parseSubsidy = (scheme) => {
  const text = `${scheme.brief_description || ''} ${scheme.eligibility || ''}`;
  const m = text.match(/(\d{1,3})\s*%/);
  return m ? Number(m[1]) : null;
};

const inferCategory = (scheme) => {
  const text = `${scheme.name || ''} ${scheme.brief_description || ''}`.toLowerCase();
  if (/irrigation|drip|sprinkler|water/.test(text)) return 'irrigation';
  if (/plant|horticulture|orchard|nursery/.test(text)) return 'plantation';
  if (/storage|warehouse|cold storage|godown/.test(text)) return 'storage';
  if (/tractor|implement|equipment|machinery/.test(text)) return 'equipment';
  if (/subsidy|financial|loan|credit|pm-kisan|insurance/.test(text)) return 'financial';
  return 'general';
};

const inferDifficulty = (scheme) => {
  const text = `${scheme.eligibility || ''} ${scheme.how_to_apply || ''}`.toLowerCase();
  if (/online|portal|single window|self apply/.test(text)) return 'Easy';
  if (/document|verification|office|district/.test(text)) return 'Medium';
  return 'Complex';
};

const inferApprovalTime = (d) => (d === 'Easy' ? '15-30' : d === 'Medium' ? '30-60' : '45-90');

const inferDocsList = (scheme) => {
  const text = `${scheme.eligibility || ''} ${scheme.how_to_apply || ''}`.toLowerCase();
  const docs = ['Aadhaar Card', 'Bank Passbook'];
  if (/land|khasra|khatauni/.test(text)) docs.push('Land Record / Khasra');
  if (/income|certificate/.test(text)) docs.push('Income Certificate');
  if (/photo|passport/.test(text)) docs.push('Passport Photo');
  if (docs.length < 4) docs.push('Ration Card');
  return docs;
};

const eligibilityScore = (scheme, farmSize) => {
  let score = 60;
  const text = `${scheme.eligibility || ''}`.toLowerCase();
  if (/all farmer|every farmer|small and marginal/.test(text)) score += 20;
  if (farmSize === 'small' && /small|marginal/.test(text)) score += 15;
  if (farmSize === 'large' && /large|big/.test(text)) score += 15;
  if (typeof scheme.subsidy === 'number' && scheme.subsidy > 30) score += 5;
  return Math.min(score, 98);
};

const getApplyLink = (scheme) => {
  if (scheme.applyUrl && scheme.applyUrl.startsWith('http')) return scheme.applyUrl;
  const urlMatch = (scheme.applyInfo || '').match(/https?:\/\/[^\s,)]+/);
  if (urlMatch) return urlMatch[0];
  if (scheme.sourceUrl) return scheme.sourceUrl;
  return 'https://www.myscheme.gov.in/';
};

/* ── component ──────────────────────────────────────────── */
const GovernmentSchemes = () => {
  const [lang, setLang] = useState('en');
  const [step, setStep] = useState(1);

  // Step 1: farm profile
  const [state, setState] = useState('');
  const [crop, setCrop] = useState('');
  const [farmSize, setFarmSize] = useState('small');

  // Data
  const [schemes, setSchemes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 3: slide-over
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [checkedDocs, setCheckedDocs] = useState({});
  const [simpleExplanations, setSimpleExplanations] = useState({});

  const t = T[lang];

  /* ── Load schemes ─── */
  const loadSchemes = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await ApiService.getGovernmentSchemes();
      setSchemes(response);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || t.errorText);
    } finally {
      setLoading(false);
    }
  }, [t.errorText]);

  /* ── Normalize & score ─── */
  const schemeCards = useMemo(() => {
    if (!schemes) return [];

    const sourceMap = (schemes.sources || []).reduce((acc, src) => {
      const key = (src.title || '').toLowerCase();
      if (key && !acc[key]) acc[key] = src.url;
      return acc;
    }, {});

    const raw = Array.isArray(schemes.schemes) ? schemes.schemes : [];
    return raw.map((s, i) => {
      const sourceUrl = sourceMap[(s.name || '').toLowerCase()] || (schemes.sources?.[0]?.url || '');
      const subsidy = parseSubsidy(s);
      const category = inferCategory(s);
      const difficulty = inferDifficulty(s);
      const applyUrl = (s.apply_url && s.apply_url.startsWith('http')) ? s.apply_url : sourceUrl;

      const card = {
        id: `${i}-${s.name}`,
        name: s.name,
        shortDescription: s.brief_description || '',
        eligibility: s.eligibility || '',
        applyInfo: s.how_to_apply || '',
        applyUrl,
        sourceUrl,
        subsidy,
        category,
        estimatedBenefit: s.estimated_benefit || 'Refer to official source',
        docsList: inferDocsList(s),
        difficulty,
        approvalDays: inferApprovalTime(difficulty),
      };
      card.matchScore = eligibilityScore(card, farmSize);

      // Ranking score
      let rank = card.matchScore;
      if (typeof subsidy === 'number' && subsidy > 40) rank += 10;
      if (difficulty === 'Easy') rank += 5;
      card.rankScore = rank;

      return card;
    });
  }, [schemes, farmSize]);

  const topSchemes = useMemo(
    () => [...schemeCards].sort((a, b) => b.rankScore - a.rankScore).slice(0, 3),
    [schemeCards]
  );

  const orderedSources = useMemo(
    () => (schemes?.sources || []).filter((s) => s?.url).slice(0, 6),
    [schemes]
  );

  /* ── Slide-over handlers ─── */
  const openScheme = (scheme) => {
    setSelectedScheme(scheme);
    setCheckedDocs({});
    setStep(3);
  };

  const closePanel = () => {
    setSelectedScheme(null);
    setStep(2);
  };

  const toggleDoc = (doc) => setCheckedDocs((p) => ({ ...p, [doc]: !p[doc] }));

  const handleExplain = (scheme) => {
    if (simpleExplanations[scheme.id]) return;
    const explanation = lang === 'hi'
      ? `${scheme.name} योजना में ${scheme.subsidy ? `${scheme.subsidy}%` : 'उपलब्ध'} सहायता मिल सकती है। ${(CATEGORY_META[scheme.category] || CATEGORY_META.general).labelHi} श्रेणी की योजना है। ${scheme.docsList.join(', ')} जैसे दस्तावेज़ तैयार रखें।`
      : `${scheme.name} provides ${scheme.subsidy ? `${scheme.subsidy}%` : 'available'} support under the ${(CATEGORY_META[scheme.category] || CATEGORY_META.general).label} category. Keep ${scheme.docsList.slice(0, 3).join(', ')} ready and apply through the official portal.`;
    setSimpleExplanations((p) => ({ ...p, [scheme.id]: explanation }));
  };

  /* ── difficulty meta ─── */
  const diffMeta = (d) => {
    if (d === 'Easy') return { cls: 'diff-easy', label: t.easy, icon: '🟢' };
    if (d === 'Medium') return { cls: 'diff-med', label: t.med, icon: '🟡' };
    return { cls: 'diff-hard', label: t.hard, icon: '🔴' };
  };

  /* ── RENDER ─── */
  return (
    <div className="gs-page">
      {/* ── Header ── */}
      <header className="gs-header">
        <div className="gs-logo">
          <Leaf size={20} />
          <span>AgroBot</span>
        </div>
        <div className="gs-header-actions">
          <div className="gs-lang-toggle" role="group">
            <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
            <button className={lang === 'hi' ? 'active' : ''} onClick={() => setLang('hi')}>हि</button>
          </div>
          <Link to="/dashboard" className="gs-back-btn">
            <ArrowLeft size={16} /> {t.back}
          </Link>
        </div>
      </header>

      {/* ── Steps indicator ── */}
      <div className="gs-steps">
        {[1, 2, 3].map((n) => (
          <div key={n} className={`gs-step ${step >= n ? 'active' : ''} ${step === n ? 'current' : ''}`}>
            <span className="gs-step-num">{n}</span>
            <span className="gs-step-label">{t[`step${n}`]}</span>
          </div>
        ))}
      </div>

      <main className="gs-main">
        {/* ═══ STEP 1: Farm Profile ═══ */}
        {step === 1 && (
          <section className="gs-profile-card">
            <div className="gs-profile-title">
              <Landmark size={22} />
              <div>
                <h1>{t.title}</h1>
                <p>{t.subtitle}</p>
              </div>
            </div>

            <div className="gs-form">
              <label className="gs-field">
                <span>{t.state}</span>
                <select value={state} onChange={(e) => setState(e.target.value)}>
                  <option value="">{t.selectState}</option>
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>

              <label className="gs-field">
                <span>{t.crop}</span>
                <input
                  type="text" value={crop} onChange={(e) => setCrop(e.target.value)}
                  placeholder={t.cropPlaceholder}
                />
              </label>

              <div className="gs-field">
                <span>{t.farmSize}</span>
                <div className="gs-size-btns">
                  {['small', 'medium', 'large'].map((s) => (
                    <button
                      key={s} className={farmSize === s ? 'active' : ''}
                      onClick={() => setFarmSize(s)}
                    >
                      {t[s]}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {error && (
              <div className="gs-error">
                <AlertTriangle size={16} /> {error}
                <button onClick={loadSchemes}>{t.retry}</button>
              </div>
            )}

            <button
              className="gs-cta"
              onClick={loadSchemes}
              disabled={loading}
            >
              {loading ? (
                <><Loader size={18} className="gs-spin" /> {t.loading}</>
              ) : (
                <><Search size={18} /> {t.findSchemes}</>
              )}
            </button>
          </section>
        )}

        {/* ═══ STEP 2: Scheme Cards ═══ */}
        {step === 2 && !loading && (
          <>
            <div className="gs-step2-header">
              <h2>
                <Sparkles size={18} /> {t.step2}
              </h2>
              <div className="gs-step2-actions">
                <button className="gs-edit-profile" onClick={() => setStep(1)}>
                  <ArrowLeft size={14} /> {t.step1}
                </button>
                <button className="gs-refresh-btn" onClick={loadSchemes} disabled={loading}>
                  <RefreshCcw size={14} />
                </button>
              </div>
            </div>

            {error && (
              <div className="gs-error">
                <AlertTriangle size={16} /> {error}
                <button onClick={loadSchemes}>{t.retry}</button>
              </div>
            )}

            {topSchemes.length === 0 ? (
              <div className="gs-empty">
                <Landmark size={32} />
                <p>{t.noSchemes}</p>
                <button onClick={() => setStep(1)}>{t.step1}</button>
              </div>
            ) : (
              <>
                {/* ── Skeleton-free loading state handled above ── */}
                <div className="gs-scheme-list">
                  {topSchemes.map((scheme, idx) => {
                    const catMeta = CATEGORY_META[scheme.category] || CATEGORY_META.general;
                    const dm = diffMeta(scheme.difficulty);
                    const subsidyText = typeof scheme.subsidy === 'number'
                      ? `${scheme.subsidy}% ${t.subsidyLabel}` : t.infoScheme;

                    return (
                      <article
                        className="gs-card" key={scheme.id}
                        onClick={() => openScheme(scheme)}
                        role="button" tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && openScheme(scheme)}
                      >
                        {idx === 0 && (
                          <div className="gs-card-ai-badge">
                            <Sparkles size={12} /> {t.recommended}
                          </div>
                        )}

                        <div className="gs-card-top">
                          <span className="gs-card-cat">
                            {catMeta.icon} {lang === 'hi' ? catMeta.labelHi : catMeta.label}
                          </span>
                          <span className={`gs-card-subsidy ${typeof scheme.subsidy === 'number' && scheme.subsidy > 40 ? 'high' : typeof scheme.subsidy === 'number' ? 'med' : 'info'}`}>
                            {subsidyText}
                          </span>
                        </div>

                        <h3>{scheme.name}</h3>
                        <p className="gs-card-desc">{scheme.shortDescription}</p>

                        {/* Match bar */}
                        <div className="gs-match">
                          <div className="gs-match-bar">
                            <div className="gs-match-fill" style={{ width: `${scheme.matchScore}%` }} />
                          </div>
                          <span className="gs-match-pct">{scheme.matchScore}% {t.match}</span>
                        </div>

                        {/* Quick stats row */}
                        <div className="gs-card-stats">
                          <div className="gs-stat">
                            <span className="gs-stat-icon">💰</span>
                            <span className="gs-stat-val">{scheme.estimatedBenefit}</span>
                          </div>
                          <div className="gs-stat">
                            <span className="gs-stat-icon">{dm.icon}</span>
                            <span className="gs-stat-val">{dm.label}</span>
                          </div>
                          <div className="gs-stat">
                            <span className="gs-stat-icon">⏱️</span>
                            <span className="gs-stat-val">{scheme.approvalDays} {t.days}</span>
                          </div>
                        </div>

                        <div className="gs-card-arrow">
                          <ChevronRight size={20} />
                        </div>
                      </article>
                    );
                  })}
                </div>

                {/* Official links */}
                {orderedSources.length > 0 && (
                  <section className="gs-links-section">
                    <h3>{t.officialLinks}</h3>
                    <div className="gs-links-grid">
                      <a href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer">
                        🔗 {t.myScheme}
                      </a>
                      <a href="https://agricoop.nic.in/" target="_blank" rel="noreferrer">
                        🏛 {t.dept}
                      </a>
                      {orderedSources.slice(0, 4).map((src, i) => (
                        <a href={src.url} target="_blank" rel="noreferrer" key={i}>
                          📄 {src.title || t.schemePdf}
                        </a>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )}

        {/* ═══ Loading skeleton (step 2 transition) ═══ */}
        {step === 2 && loading && (
          <div className="gs-skeleton-wrap">
            <div className="gs-skeleton-bar" />
            {[1, 2, 3].map((n) => (
              <div className="gs-skeleton-card" key={n}>
                <div className="gs-skel-line w60" /><div className="gs-skel-line w90" />
                <div className="gs-skel-line w40" /><div className="gs-skel-line w70" />
              </div>
            ))}
          </div>
        )}
      </main>

      {/* ═══ STEP 3: Slide-over Panel ═══ */}
      {selectedScheme && (
        <>
          <div className="gs-overlay" onClick={closePanel} />
          <aside className="gs-panel">
            <div className="gs-panel-header">
              <h2>{t.step3}</h2>
              <button className="gs-panel-close" onClick={closePanel}>
                <X size={20} />
              </button>
            </div>

            <div className="gs-panel-body">
              <div className="gs-panel-badge-row">
                <span className="gs-card-cat">
                  {(CATEGORY_META[selectedScheme.category] || CATEGORY_META.general).icon}{' '}
                  {lang === 'hi'
                    ? (CATEGORY_META[selectedScheme.category] || CATEGORY_META.general).labelHi
                    : (CATEGORY_META[selectedScheme.category] || CATEGORY_META.general).label}
                </span>
                <span className={`gs-card-subsidy ${typeof selectedScheme.subsidy === 'number' && selectedScheme.subsidy > 40 ? 'high' : typeof selectedScheme.subsidy === 'number' ? 'med' : 'info'}`}>
                  {typeof selectedScheme.subsidy === 'number' ? `${selectedScheme.subsidy}% ${t.subsidyLabel}` : t.infoScheme}
                </span>
              </div>

              <h3 className="gs-panel-name">{selectedScheme.name}</h3>
              <p className="gs-panel-desc">{selectedScheme.shortDescription}</p>

              {/* Match */}
              <div className="gs-match gs-match-lg">
                <div className="gs-match-bar"><div className="gs-match-fill" style={{ width: `${selectedScheme.matchScore}%` }} /></div>
                <span className="gs-match-pct">{selectedScheme.matchScore}% {t.match}</span>
              </div>

              {/* Benefit / Difficulty / Time */}
              <div className="gs-panel-stats">
                <div><span>💰</span><strong>{t.benefit}</strong><p>{selectedScheme.estimatedBenefit}</p></div>
                <div><span>{diffMeta(selectedScheme.difficulty).icon}</span><strong>{t.difficulty}</strong><p>{diffMeta(selectedScheme.difficulty).label}</p></div>
                <div><span>⏱️</span><strong>{t.approval}</strong><p>{selectedScheme.approvalDays} {t.days}</p></div>
              </div>

              {/* Eligibility */}
              <details className="gs-panel-section" open>
                <summary><ShieldCheck size={16} /> {t.eligibility}</summary>
                <p>{selectedScheme.eligibility || '—'}</p>
              </details>

              {/* How to apply */}
              <details className="gs-panel-section">
                <summary><FileText size={16} /> {t.howToApply}</summary>
                <p>{selectedScheme.applyInfo || '—'}</p>
              </details>

              {/* Documents checklist */}
              <details className="gs-panel-section" open>
                <summary><CheckCircle2 size={16} /> {t.docsChecklist}</summary>
                <ul className="gs-docs-list">
                  {selectedScheme.docsList.map((doc) => (
                    <li key={doc} className={checkedDocs[doc] ? 'checked' : ''} onClick={() => toggleDoc(doc)}>
                      <span className="gs-doc-check">{checkedDocs[doc] ? '✅' : '⬜'}</span>
                      {doc}
                    </li>
                  ))}
                </ul>
                {selectedScheme.docsList.some((d) => !checkedDocs[d]) && (
                  <div className="gs-doc-warning">
                    <AlertTriangle size={14} /> {lang === 'hi' ? 'कुछ दस्तावेज़ अभी तैयार नहीं हैं' : 'Some documents are not ready yet'}
                  </div>
                )}
              </details>

              {/* Explain simply */}
              <button className="gs-explain-btn" onClick={() => handleExplain(selectedScheme)}>
                {t.explain}
              </button>
              {simpleExplanations[selectedScheme.id] && (
                <div className="gs-explanation">
                  🤖 {simpleExplanations[selectedScheme.id]}
                </div>
              )}

              {/* Why recommended */}
              <div className="gs-why">
                <Sparkles size={14} /> <strong>{t.whyRecommended}</strong>{' '}
                {lang === 'hi'
                  ? `आपके ${farmSize === 'small' ? 'छोटे' : farmSize === 'medium' ? 'मध्यम' : 'बड़े'} खेत और ${state || 'आपके राज्य'} के लिए ${selectedScheme.matchScore}% मिलान।`
                  : `${selectedScheme.matchScore}% match for your ${farmSize} farm in ${state || 'your state'}.`}
              </div>
            </div>

            {/* Actions */}
            <div className="gs-panel-footer">
              <a
                className="gs-apply-btn"
                href={getApplyLink(selectedScheme)}
                target="_blank" rel="noreferrer"
              >
                <ExternalLink size={16} /> {t.apply}
              </a>
              <button className="gs-prepare-btn" onClick={closePanel}>
                <FileText size={16} /> {t.prepareDocs}
              </button>
            </div>
          </aside>
        </>
      )}
    </div>
  );
};

export default GovernmentSchemes;
