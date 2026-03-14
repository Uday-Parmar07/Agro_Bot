import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Leaf, Upload, Camera, ArrowLeft, Search, RotateCcw, ChevronRight,
  Sun, Focus, ImageOff, AlertTriangle, CheckCircle2, XCircle, Shield,
  Sparkles, Bug, Pill, ShieldCheck, Info, Loader2, X,
} from 'lucide-react';
import ApiService from '../services/api';
import './DiseaseCheckup.css';

/* ── i18n ── */
const T = {
  en: {
    brand: 'AgroBot',
    back: 'Dashboard',
    step1: 'Upload',
    step2: 'Analyze',
    step3: 'Results',
    title: 'Plant Disease Detection',
    subtitle: 'Upload or capture a leaf image — AI will identify the disease and suggest treatment.',
    dragDrop: 'Drag & drop leaf image here',
    or: 'or',
    uploadBtn: 'Upload Image',
    cameraBtn: 'Use Camera',
    tipsTitle: 'Tips for best results',
    tip1: 'Take photo in bright daylight',
    tip2: 'Focus on a single leaf',
    tip3: 'Avoid blurry or dark images',
    accepted: 'JPG, PNG only • Max 10 MB',
    changeImg: 'Change Image',
    analyzeBtn: 'Analyze Leaf',
    analyzing: 'AI is scanning your leaf…',
    lowConf: 'Image unclear — the AI isn\'t confident enough. Try a clearer photo.',
    tryAnother: 'Try Another Photo',
    retry: 'Retry',
    detected: 'Disease Detected',
    healthy: 'Healthy Leaf',
    confidence: 'Confidence',
    cause: 'Possible Cause',
    treatment: 'Treatment',
    prevention: 'Prevention Tips',
    whyDetected: 'Why this was detected',
    detailedSolution: 'View Detailed Solution',
    scanAnother: 'Scan Another Leaf',
    aiPowered: 'AI-Powered Analysis',
    invalidFormat: 'Invalid format. Please upload JPG or PNG.',
    tooLarge: 'Image too large. Max size is 10 MB.',
    uploadFailed: 'Upload failed. Please try again.',
    networkError: 'Network error. Check your connection and retry.',
    exampleTitle: 'Example: Good vs Bad Photos',
  },
  hi: {
    brand: 'एग्रोबॉट',
    back: 'डैशबोर्ड',
    step1: 'अपलोड',
    step2: 'जाँच',
    step3: 'परिणाम',
    title: 'पौधे की बीमारी जाँच',
    subtitle: 'पत्ती की तस्वीर अपलोड करें — AI बीमारी पहचानेगा और इलाज बताएगा।',
    dragDrop: 'पत्ती की तस्वीर यहाँ खींचें',
    or: 'या',
    uploadBtn: 'तस्वीर अपलोड करें',
    cameraBtn: 'कैमरा खोलें',
    tipsTitle: 'अच्छी तस्वीर के लिए',
    tip1: 'धूप में तस्वीर लें',
    tip2: 'एक पत्ती पर फोकस करें',
    tip3: 'धुंधली तस्वीर न लें',
    accepted: 'केवल JPG, PNG • अधिकतम 10 MB',
    changeImg: 'तस्वीर बदलें',
    analyzeBtn: 'पत्ती की जाँच करें',
    analyzing: 'AI आपकी पत्ती जाँच रहा है…',
    lowConf: 'तस्वीर स्पष्ट नहीं है — कृपया दूसरी तस्वीर लें।',
    tryAnother: 'दूसरी तस्वीर लें',
    retry: 'पुनः प्रयास',
    detected: 'बीमारी पाई गई',
    healthy: 'स्वस्थ पत्ती',
    confidence: 'विश्वसनीयता',
    cause: 'संभावित कारण',
    treatment: 'उपचार',
    prevention: 'रोकथाम',
    whyDetected: 'यह क्यों पहचाना गया',
    detailedSolution: 'विस्तृत समाधान देखें',
    scanAnother: 'दूसरी पत्ती जाँचें',
    aiPowered: 'AI विश्लेषण',
    invalidFormat: 'गलत फार्मेट। कृपया JPG या PNG अपलोड करें।',
    tooLarge: 'तस्वीर बहुत बड़ी। अधिकतम 10 MB।',
    tooLargeDesc: '',
    uploadFailed: 'अपलोड विफल। पुनः प्रयास करें।',
    networkError: 'नेटवर्क त्रुटि। कनेक्शन जाँचें और पुनः प्रयास करें।',
    exampleTitle: 'उदाहरण: अच्छी व खराब तस्वीर',
  },
};

const VALID_TYPES = ['image/jpeg', 'image/png', 'image/jpg'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB
const LOW_CONFIDENCE = 0.45;

/* ── helpers ── */
const isHealthy = (cls) => /healthy/i.test(cls || '');
const confPct = (c) => `${(c * 100).toFixed(1)}%`;
const confColor = (c) => (c >= 0.85 ? '#10b981' : c >= 0.6 ? '#f59e0b' : '#ef4444');

const DiseaseCheckup = () => {
  const [lang, setLang] = useState('en');
  const t = T[lang];

  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const fileRef = useRef(null);
  const cameraRef = useRef(null);

  const previewUrl = useMemo(() => {
    if (!file) return '';
    return URL.createObjectURL(file);
  }, [file]);

  /* ── file validation ── */
  const validateAndSet = useCallback((f) => {
    if (!f) return;
    if (!VALID_TYPES.includes(f.type)) {
      setError(t.invalidFormat);
      return;
    }
    if (f.size > MAX_SIZE) {
      setError(t.tooLarge);
      return;
    }
    setFile(f);
    setError('');
    setResult(null);
    setStep(2);
  }, [t]);

  const handleFileChange = (e) => validateAndSet(e.target.files?.[0]);

  /* ── drag & drop ── */
  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    validateAndSet(e.dataTransfer.files?.[0]);
  };

  /* ── predict ── */
  const handlePredict = async () => {
    if (!file) return;
    try {
      setLoading(true);
      setError('');
      const response = await ApiService.predictDiseaseImage(file);
      setResult(response);
      setStep(3);
    } catch (err) {
      const msg = err.response?.data?.detail || (err.code === 'ERR_NETWORK' ? t.networkError : t.uploadFailed);
      setError(msg);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  /* ── reset ── */
  const resetAll = () => {
    setFile(null);
    setResult(null);
    setError('');
    setStep(1);
    setDetailOpen(false);
    if (fileRef.current) fileRef.current.value = '';
    if (cameraRef.current) cameraRef.current.value = '';
  };

  const goToStep2 = () => { setResult(null); setError(''); setStep(2); };

  const lowConfidence = result && result.confidence < LOW_CONFIDENCE;
  const healthy = result && isHealthy(result.predicted_class);

  /* ═══════════════════════ RENDER ═══════════════════════ */
  return (
    <div className="dc-page">
      {/* ── header ── */}
      <header className="dc-header">
        <div className="dc-logo"><Leaf size={20} /><span>{t.brand}</span></div>
        <div className="dc-header-actions">
          <div className="dc-lang-toggle">
            <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
            <button className={lang === 'hi' ? 'active' : ''} onClick={() => setLang('hi')}>हिं</button>
          </div>
          <Link to="/dashboard" className="dc-back-btn"><ArrowLeft size={14} />{t.back}</Link>
        </div>
      </header>

      {/* ── step indicator ── */}
      <div className="dc-steps">
        {[t.step1, t.step2, t.step3].map((label, i) => (
          <div key={i} className={`dc-step ${step > i + 1 ? 'active' : ''} ${step === i + 1 ? 'current' : ''}`}>
            <span className="dc-step-num">{i + 1}</span>
            <span className="dc-step-label">{label}</span>
          </div>
        ))}
      </div>

      <main className="dc-main">
        {/* ═══ STEP 1: Upload ═══ */}
        {step === 1 && (
          <div className="dc-upload-card">
            <div className="dc-upload-title">
              <span style={{ fontSize: 32 }}>🔬</span>
              <div>
                <h1>{t.title}</h1>
                <p>{t.subtitle}</p>
              </div>
            </div>

            {/* drop zone */}
            <div
              className={`dc-dropzone ${dragOver ? 'drag-over' : ''}`}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
            >
              <Upload size={36} style={{ color: '#60a5fa', marginBottom: 8 }} />
              <p className="dc-drop-text">{t.dragDrop}</p>
              <span className="dc-drop-or">{t.or}</span>
              <div className="dc-drop-btns">
                <button className="dc-upload-btn" onClick={() => fileRef.current?.click()}>
                  <Upload size={16} />{t.uploadBtn}
                </button>
                <button className="dc-camera-btn" onClick={() => cameraRef.current?.click()}>
                  <Camera size={16} />{t.cameraBtn}
                </button>
              </div>
              <span className="dc-accepted">{t.accepted}</span>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png" onChange={handleFileChange} hidden />
              <input ref={cameraRef} type="file" accept="image/jpeg,image/png" capture="environment" onChange={handleFileChange} hidden />
            </div>

            {/* tips */}
            <div className="dc-tips">
              <h3>{t.tipsTitle}</h3>
              <div className="dc-tips-grid">
                <div className="dc-tip"><Sun size={18} color="#fbbf24" /><span>{t.tip1}</span></div>
                <div className="dc-tip"><Focus size={18} color="#34d399" /><span>{t.tip2}</span></div>
                <div className="dc-tip"><ImageOff size={18} color="#f87171" /><span>{t.tip3}</span></div>
              </div>
            </div>

            {error && (
              <div className="dc-error">
                <AlertTriangle size={16} />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}

        {/* ═══ STEP 2: Analyze ═══ */}
        {step === 2 && (
          <div className="dc-analyze-card">
            <div className="dc-preview-section">
              {previewUrl && (
                <div className="dc-preview-wrap">
                  <img src={previewUrl} alt="Leaf preview" className="dc-preview-img" />
                  <button className="dc-change-img" onClick={resetAll}><X size={14} />{t.changeImg}</button>
                </div>
              )}
            </div>

            {!loading ? (
              <button className="dc-cta" onClick={handlePredict} disabled={!file}>
                <Search size={18} />{t.analyzeBtn}<ChevronRight size={16} />
              </button>
            ) : (
              <div className="dc-scanning">
                <div className="dc-scan-anim">
                  <div className="dc-scan-ring" />
                  <Leaf size={28} className="dc-scan-leaf" />
                </div>
                <p>{t.analyzing}</p>
                <div className="dc-scan-bar"><div className="dc-scan-fill" /></div>
              </div>
            )}

            {error && (
              <div className="dc-error">
                <AlertTriangle size={16} />
                <span>{error}</span>
                <button onClick={handlePredict}>{t.retry}</button>
              </div>
            )}
          </div>
        )}

        {/* ═══ STEP 3: Results ═══ */}
        {step === 3 && result && (
          <div className="dc-result-wrap">
            {/* LOW CONFIDENCE warning */}
            {lowConfidence && (
              <div className="dc-low-conf">
                <AlertTriangle size={20} color="#fbbf24" />
                <div>
                  <p>{t.lowConf}</p>
                  <button onClick={resetAll}>{t.tryAnother}</button>
                </div>
              </div>
            )}

            {/* result card */}
            <div className={`dc-result-card ${healthy ? 'healthy' : 'diseased'}`}>
              {/* header badge */}
              <div className="dc-result-badge-row">
                <span className="dc-ai-badge"><Sparkles size={12} />{t.aiPowered}</span>
                {result.llm_enhanced && <span className="dc-llm-badge">LLM Enhanced</span>}
              </div>

              {/* image + status */}
              <div className="dc-result-top">
                {previewUrl && <img src={previewUrl} alt="Analyzed leaf" className="dc-result-thumb" />}
                <div className="dc-result-status">
                  <div className={`dc-status-icon ${healthy ? 'healthy' : 'diseased'}`}>
                    {healthy ? <CheckCircle2 size={28} /> : <XCircle size={28} />}
                  </div>
                  <div>
                    <h2>{healthy ? t.healthy : t.detected}</h2>
                    <p className="dc-disease-name">{result.predicted_class.replace(/_/g, ' ')}</p>
                  </div>
                </div>
              </div>

              {/* confidence meter */}
              <div className="dc-conf-section">
                <span className="dc-conf-label">{t.confidence}</span>
                <div className="dc-conf-bar">
                  <div
                    className="dc-conf-fill"
                    style={{ width: confPct(result.confidence), background: confColor(result.confidence) }}
                  />
                </div>
                <span className="dc-conf-pct" style={{ color: confColor(result.confidence) }}>
                  {confPct(result.confidence)}
                </span>
              </div>

              {/* detail sections */}
              {!healthy && (
                <div className="dc-detail-sections">
                  {/* cause */}
                  {result.possible_cause && (
                    <div className="dc-detail-box cause">
                      <div className="dc-detail-icon"><Bug size={16} /></div>
                      <div>
                        <strong>{t.cause}</strong>
                        <p>{result.possible_cause}</p>
                      </div>
                    </div>
                  )}

                  {/* treatment */}
                  {result.treatment && (
                    <div className="dc-detail-box treatment">
                      <div className="dc-detail-icon"><Pill size={16} /></div>
                      <div>
                        <strong>{t.treatment}</strong>
                        <p>{result.treatment}</p>
                      </div>
                    </div>
                  )}

                  {/* prevention (from detailed_classification) */}
                  {result.detailed_classification && (
                    <details className="dc-expandable">
                      <summary><ShieldCheck size={16} />{t.detailedSolution}</summary>
                      <p>{result.detailed_classification}</p>
                    </details>
                  )}
                </div>
              )}

              {/* healthy message */}
              {healthy && (
                <div className="dc-healthy-msg">
                  <Shield size={20} />
                  <p>{result.detailed_classification || 'Your plant looks healthy! No disease detected.'}</p>
                </div>
              )}
            </div>

            {/* action buttons */}
            <div className="dc-result-actions">
              <button className="dc-scan-again" onClick={resetAll}>
                <RotateCcw size={16} />{t.scanAnother}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default DiseaseCheckup;
