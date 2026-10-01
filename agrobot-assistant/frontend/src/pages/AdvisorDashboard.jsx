import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Search, X } from 'lucide-react';
import ApiService from '../services/api';
import './FeaturePages.css';

const ICON = { strokeWidth: 2.75 };

/* Risk is what an advisor scans for, so it sorts first and is shown as a
   labelled tone chip rather than a bare number. */
const riskOf = (farmer) => {
  if (farmer.disease_checks_30d >= 3) return { tone: 'urgent', label: 'High risk' };
  if (farmer.latest_soil_score !== null && farmer.latest_soil_score !== undefined && farmer.latest_soil_score < 6.5) {
    return { tone: 'caution', label: 'Watch' };
  }
  if (farmer.latest_soil_score === null || farmer.latest_soil_score === undefined) {
    return { tone: 'unknown', label: 'Not assessed' };
  }
  return { tone: 'good', label: 'Stable' };
};

const RISK_ORDER = { urgent: 0, caution: 1, unknown: 2, good: 3 };

const AdvisorDashboard = () => {
  const [farmers, setFarmers] = useState([]);
  const [summary, setSummary] = useState(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    ApiService.getAdvisorFarmers()
      .then((data) => setFarmers(data || []))
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load advisor data.'))
      .finally(() => setLoading(false));
  }, []);

  const loadSummary = async (farmerId) => {
    try {
      const data = await ApiService.getAdvisorFarmerSummary(farmerId);
      setSummary(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load that farmer.');
    }
  };

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return farmers
      .filter((farmer) => !needle
        || `${farmer.full_name || ''} ${farmer.email || ''}`.toLowerCase().includes(needle))
      .slice()
      .sort((a, b) => RISK_ORDER[riskOf(a).tone] - RISK_ORDER[riskOf(b).tone]);
  }, [farmers, query]);

  /* The detail opens in place of the list, not appended below it. */
  if (summary) {
    return (
      <div className="feature-page">
        <div className="feature-container">
          <header className="feature-header">
            <div>
              <h1>{summary.full_name}</h1>
              <p>Farmer summary and risk flags.</p>
            </div>
            <button type="button" className="feature-button secondary" onClick={() => setSummary(null)}>
              <ArrowLeft size={16} {...ICON} /> All farmers
            </button>
          </header>

          <section className="feature-card">
            <h3>Activity</h3>
            <dl className="feature-card-stats">
              <div><dt>Disease checks</dt><dd>{summary.disease_checks}</dd></div>
              <div><dt>Weather snapshots</dt><dd>{summary.weather_snapshots}</dd></div>
              <div><dt>Flags</dt><dd>{summary.disease_flags.length}</dd></div>
            </dl>
            <div className="feature-flags">
              {summary.disease_flags.length
                ? summary.disease_flags.map((flag) => (
                  <span key={flag} className="tag tag-caution">{flag.replace(/_/g, ' ')}</span>
                ))
                : <span className="tag tag-good">No flags</span>}
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="feature-page">
      <div className="feature-container">
        <header className="feature-header">
          <div>
            <h1>Advisor Dashboard</h1>
            <p>Assigned farmer history and risk flags.</p>
          </div>
          <Link className="feature-button secondary" to="/dashboard">
            <ArrowLeft size={16} {...ICON} /> Dashboard
          </Link>
        </header>

        {error && <div className="feature-card">{error}</div>}

        <div className="feature-toolbar">
          <label className="feature-search">
            <span className="sr-only">Search farmers</span>
            <span style={{ position: 'relative', display: 'block' }}>
              <Search
                size={18}
                {...ICON}
                style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-muted)' }}
              />
              <input
                className="input"
                style={{ paddingLeft: 46 }}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by name or email"
              />
            </span>
          </label>
          {query && (
            <button type="button" className="feature-button secondary" onClick={() => setQuery('')}>
              <X size={16} {...ICON} /> Clear
            </button>
          )}
          <span className="feature-count">
            {loading ? 'Loading…' : `${visible.length} of ${farmers.length} farmers`}
          </span>
        </div>

        {!loading && farmers.length === 0 && (
          <div className="feature-empty">
            <p>No farmers are assigned to you yet.</p>
          </div>
        )}

        {!loading && farmers.length > 0 && visible.length === 0 && (
          <div className="feature-empty">
            <p>No farmer matches “{query}”.</p>
          </div>
        )}

        <section className="feature-grid">
          {visible.map((farmer) => {
            const risk = riskOf(farmer);
            return (
              <article key={farmer.farmer_id} className="feature-card">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                  <h3 style={{ flex: 1, minWidth: 0 }}>{farmer.full_name}</h3>
                  <span className={`tag tag-${risk.tone}`}>{risk.label}</span>
                </div>
                <p className="feature-card-email">{farmer.email}</p>
                <dl className="feature-card-stats">
                  <div><dt>Farms</dt><dd>{farmer.farms_count}</dd></div>
                  <div>
                    <dt>Soil score</dt>
                    <dd>{farmer.latest_soil_score ?? '—'}</dd>
                  </div>
                  <div><dt>Checks / 30d</dt><dd>{farmer.disease_checks_30d}</dd></div>
                </dl>
                <div className="feature-actions">
                  <button type="button" className="feature-button" onClick={() => loadSummary(farmer.farmer_id)}>
                    View summary
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      </div>
    </div>
  );
};

export default AdvisorDashboard;
