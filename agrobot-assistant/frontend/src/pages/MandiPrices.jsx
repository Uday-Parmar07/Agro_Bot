import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowUpRight,
  ExternalLink,
  IndianRupee,
  Leaf,
  Loader,
  MapPin,
  Navigation,
  Newspaper,
  Plus,
  RefreshCcw,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import ApiService from '../services/api';
import '../components/MandiPrices.css';

const T = {
  en: {
    title: 'Mandi Prices',
    subtitle: 'Check local crop value, better markets, price trend, and market news',
    back: 'Dashboard',
    crop: 'Crop',
    market: 'Market',
    state: 'State',
    district: 'District',
    allStates: 'All states',
    allDistricts: 'All districts',
    selectMarket: 'Farm nearest mandi',
    searchCrop: 'Search any Agmarknet crop',
    savedCrops: 'Saved crops',
    addToCrops: 'Add to my crops',
    addedToCrops: 'Added to my crops',
    min: 'Min',
    max: 'Max',
    modal: 'Modal',
    basedOnFarm: 'Trip math is based on your farm location',
    trendWhy: 'This trend may be connected to',
    loading: 'Loading mandi prices...',
    localPrice: 'Local Price',
    worthTrip: 'Worth the Trip',
    trend: '30 Day Trend',
    news: 'Market News',
    noCrops: 'Add a crop from the dashboard to check mandi prices.',
    addCrop: 'Add Crop',
    noTrip: 'No better nearby mandi clears the net-gain threshold.',
    noNews: 'No relevant market news found for this crop today.',
    refresh: 'Refresh',
    stateAvg: 'State avg',
    indiaAvg: 'India avg',
    netGain: 'net gain',
    why: 'Possible reason',
  },
  hi: {
    title: 'मंडी भाव',
    subtitle: 'स्थानीय भाव, बेहतर मंडी, भाव रुझान और बाजार समाचार देखें',
    back: 'डैशबोर्ड',
    crop: 'फसल',
    market: 'मंडी',
    state: 'राज्य',
    district: 'जिला',
    allStates: 'सभी राज्य',
    allDistricts: 'सभी जिले',
    selectMarket: 'खेत के पास की मंडी',
    searchCrop: 'Agmarknet की कोई भी फसल खोजें',
    savedCrops: 'सहेजी गई फसलें',
    addToCrops: 'मेरी फसलों में जोड़ें',
    addedToCrops: 'मेरी फसलों में जुड़ गई',
    min: 'न्यूनतम',
    max: 'अधिकतम',
    modal: 'मोडल',
    basedOnFarm: 'यात्रा गणना आपके खेत की लोकेशन पर आधारित है',
    trendWhy: 'यह रुझान इससे जुड़ा हो सकता है',
    loading: 'मंडी भाव लोड हो रहे हैं...',
    localPrice: 'स्थानीय भाव',
    worthTrip: 'यात्रा लाभदायक?',
    trend: '30 दिन का रुझान',
    news: 'बाजार समाचार',
    noCrops: 'मंडी भाव देखने के लिए डैशबोर्ड से फसल जोड़ें।',
    addCrop: 'फसल जोड़ें',
    noTrip: 'कोई बेहतर नजदीकी मंडी खर्च के बाद लाभ सीमा पार नहीं करती।',
    noNews: 'आज इस फसल के लिए संबंधित बाजार समाचार नहीं मिला।',
    refresh: 'रीफ्रेश',
    stateAvg: 'राज्य औसत',
    indiaAvg: 'भारत औसत',
    netGain: 'शुद्ध लाभ',
    why: 'संभावित कारण',
  },
};

export const findTrendWhy = (direction, insights = []) => {
  if (!['up', 'down'].includes(direction)) return null;
  const upPatterns = [
    /\bmsp\b/i,
    /\bhike\b/i,
    /\bincrease\b/i,
    /\brise\b/i,
    /\bshortage\b/i,
    /\blower arrivals?\b/i,
    /\bexport demand\b/i,
    /\bexports? rise\b/i,
  ];
  const downPatterns = [
    /\bglut\b/i,
    /\bsurplus\b/i,
    /\bfall\b/i,
    /\bdecline\b/i,
    /\bdrop\b/i,
    /\bhigher arrivals?\b/i,
    /\bimport\b/i,
    /\bexport ban\b/i,
    /\bexport restriction\b/i,
  ];
  const patterns = direction === 'up' ? upPatterns : downPatterns;
  return insights.find((item) => {
    const text = `${item.headline || ''} ${item.summary || ''}`;
    return patterns.some((pattern) => pattern.test(text));
  }) || null;
};

const formatPrice = (value) => {
  if (value === null || value === undefined) return 'No data';
  return `Rs. ${Number(value).toLocaleString('en-IN')}/q`;
};

const formatMoney = (value) => `Rs. ${Math.round(value || 0).toLocaleString('en-IN')}`;

const formatDate = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
};

const shortDate = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
};

const fullDate = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const Sparkline = ({ points = [] }) => {
  const priced = points.filter((point) => point.modal_price !== null && point.modal_price !== undefined);
  if (priced.length < 2) {
    return <div className="mandi-sparkline-empty">No trend</div>;
  }

  const values = priced.map((point) => Number(point.modal_price));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const plotted = priced.map((point, index) => {
    const x = (index / Math.max(priced.length - 1, 1)) * 100;
    const y = 34 - ((Number(point.modal_price) - min) / spread) * 28;
    return { ...point, x, y };
  });
  const coords = plotted.map((point) => `${point.x},${point.y}`).join(' ');
  const tickIndexes = [0, Math.floor((priced.length - 1) / 2), priced.length - 1];

  return (
    <div className="mandi-chart-wrap">
      <svg className="mandi-sparkline" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label="Price trend chart">
        <polyline points={coords} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {plotted.map((point) => (
          <circle key={`${point.date}-${point.modal_price}`} cx={point.x} cy={point.y} r="1.8" className="mandi-chart-point">
            <title>{fullDate(point.date)} - {formatPrice(point.modal_price)}</title>
          </circle>
        ))}
      </svg>
      <div className="mandi-axis-labels">
        {tickIndexes.map((index) => (
          <span key={index}>{shortDate(priced[index]?.date)}</span>
        ))}
      </div>
    </div>
  );
};

const MandiPrices = () => {
  const savedLang = localStorage.getItem('preferred_language') || 'en';
  const [lang, setLang] = useState(savedLang.startsWith('hi') ? 'hi' : 'en');
  const [farms, setFarms] = useState([]);
  const [farmId, setFarmId] = useState(null);
  const [crops, setCrops] = useState([]);
  const [selectedCrop, setSelectedCrop] = useState('');
  const [cropQuery, setCropQuery] = useState('');
  const [commodityOptions, setCommodityOptions] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState({ state: '', district: '', market: '' });
  const [current, setCurrent] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [trend, setTrend] = useState(null);
  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [addingCrop, setAddingCrop] = useState(false);
  const [addedCrop, setAddedCrop] = useState('');

  const t = T[lang];

  useEffect(() => {
    const loadFarms = async () => {
      setLoading(true);
      setError('');
      try {
        const farmList = await ApiService.getFarms();
        const firstFarm = (farmList || [])[0];
        setFarms(farmList || []);
        setFarmId(firstFarm?.id || null);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || 'Unable to load mandi prices.');
      } finally {
        setLoading(false);
      }
    };

    loadFarms();
  }, []);

  useEffect(() => {
    if (!farmId) return;

    const loadCrops = async () => {
      setLoading(true);
      setError('');
      try {
        const cropList = await ApiService.getFarmCrops(farmId);
        setCrops(cropList || []);
        const firstCrop = (cropList || [])[0]?.crop_name || '';
        setSelectedCrop(firstCrop);
        setCropQuery(firstCrop);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || 'Unable to load farm crops.');
      } finally {
        setLoading(false);
      }
    };

    loadCrops();
  }, [farmId]);

  useEffect(() => {
    const loadLocations = async () => {
      try {
        const response = await ApiService.getMandiLocations();
        setLocations(response.locations || []);
      } catch (locationError) {
        setLocations([]);
      }
    };

    loadLocations();
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const response = await ApiService.searchMandiCommodities(cropQuery);
        setCommodityOptions(response.commodities || []);
        if (!selectedCrop && response.commodities?.[0]) {
          setSelectedCrop(response.commodities[0]);
          setCropQuery(response.commodities[0]);
        }
      } catch (commodityError) {
        setCommodityOptions([]);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [cropQuery, selectedCrop]);

  useEffect(() => {
    if (!farmId || !selectedCrop) {
      setCurrent(null);
      setComparison(null);
      setTrend(null);
      setNews(null);
      return;
    }

    const loadMandiData = async () => {
      setLoading(true);
      setError('');
      try {
        const currentResult = await ApiService.getMandiCurrent(farmId, selectedCrop, selectedLocation);
        setCurrent(currentResult);
        const primaryMarket = currentResult.primary_market || currentResult.nearby?.[0]?.market_name;
        const primary = currentResult.nearby?.[0];
        if (!selectedLocation.market && primary?.market_name) {
          setSelectedLocation({
            state: primary.state || '',
            district: primary.district || '',
            market: primary.market_name,
          });
        }
        const [compareResult, trendResult, newsResult] = await Promise.all([
          ApiService.compareMandiPrices(farmId, selectedCrop, 250).catch(() => null),
          primaryMarket ? ApiService.getMandiTrend(primaryMarket, selectedCrop, 30).catch(() => null) : Promise.resolve(null),
          ApiService.getMandiNews(selectedCrop).catch(() => null),
        ]);
        setComparison(compareResult);
        setTrend(trendResult);
        setNews(newsResult);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || 'Unable to load mandi prices.');
      } finally {
        setLoading(false);
      }
    };

    loadMandiData();
  }, [farmId, selectedCrop, selectedLocation]);

  const primary = current?.nearby?.find((item) => item.modal_price !== null && item.modal_price !== undefined) || current?.nearby?.[0];
  const selectedFarm = farms.find((farm) => farm.id === farmId);
  const savedCropNames = useMemo(
    () => crops.map((crop) => crop.crop_name).filter(Boolean),
    [crops]
  );
  const isTrackedCrop = savedCropNames.some((crop) => crop.toLowerCase() === (selectedCrop || '').toLowerCase());
  const pinnedCommodities = useMemo(() => {
    const merged = [...savedCropNames, ...commodityOptions];
    const seen = new Set();
    return merged.filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [savedCropNames, commodityOptions]);
  const locationStates = useMemo(
    () => [...new Set(locations.map((item) => item.state).filter(Boolean))].sort(),
    [locations]
  );
  const locationDistricts = useMemo(
    () => [...new Set(
      locations
        .filter((item) => !selectedLocation.state || item.state === selectedLocation.state)
        .map((item) => item.district)
        .filter(Boolean)
    )].sort(),
    [locations, selectedLocation.state]
  );
  const locationMarkets = useMemo(
    () => locations.filter((item) => (
      (!selectedLocation.state || item.state === selectedLocation.state)
      && (!selectedLocation.district || item.district === selectedLocation.district)
    )),
    [locations, selectedLocation.state, selectedLocation.district]
  );
  const trendRange = useMemo(() => {
    const points = (trend?.points || []).filter((point) => point.date);
    if (!points.length) return '';
    return `${shortDate(points[0].date)} - ${shortDate(points[points.length - 1].date)}`;
  }, [trend?.points]);
  const trendWhy = useMemo(
    () => findTrendWhy(trend?.direction, news?.insights || []),
    [trend?.direction, news?.insights]
  );
  const TrendIcon = trend?.direction === 'down' ? TrendingDown : TrendingUp;

  const handleCropSelect = (cropName) => {
    setSelectedCrop(cropName);
    setCropQuery(cropName);
    setAddedCrop('');
  };

  const handleAddViewedCrop = async () => {
    if (!farmId || !selectedCrop || isTrackedCrop) return;
    setAddingCrop(true);
    try {
      const saved = await ApiService.createFarmCrop({
        farm_id: farmId,
        crop_name: selectedCrop,
        added_by: 'user',
      });
      setCrops((prev) => [saved, ...prev]);
      setAddedCrop(selectedCrop);
    } catch (addError) {
      setError(addError.response?.data?.detail || 'Unable to add crop.');
    } finally {
      setAddingCrop(false);
    }
  };

  return (
    <div className="mandi-page">
      <header className="mandi-page-header">
        <div className="mandi-logo">
          <Leaf size={20} />
          <span>AgroBot</span>
        </div>
        <div className="mandi-page-actions">
          <div className="mandi-lang-toggle" role="group">
            <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
            <button className={lang === 'hi' ? 'active' : ''} onClick={() => setLang('hi')}>हि</button>
          </div>
          <Link to="/dashboard" className="mandi-back-btn">
            <ArrowLeft size={16} /> {t.back}
          </Link>
        </div>
      </header>

      <main className="mandi-page-main">
        <section className="mandi-page-hero">
          <div>
            <h1>{t.title}</h1>
            <p>{t.subtitle}</p>
          </div>
          <div className="mandi-page-controls">
            {farms.length > 1 && (
              <select value={farmId || ''} onChange={(event) => setFarmId(Number(event.target.value))}>
                {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
              </select>
            )}
            <label className="mandi-combobox">
              <span>{t.crop}</span>
              <input
                value={cropQuery}
                onChange={(event) => {
                  setCropQuery(event.target.value);
                  setSelectedCrop(event.target.value);
                  setAddedCrop('');
                }}
                placeholder={t.searchCrop}
              />
              <div className="mandi-combobox-list">
                {pinnedCommodities.slice(0, 8).map((cropName) => (
                  <button
                    key={cropName}
                    type="button"
                    className={cropName.toLowerCase() === (selectedCrop || '').toLowerCase() ? 'active' : ''}
                    onClick={() => handleCropSelect(cropName)}
                  >
                    {cropName}
                    {savedCropNames.some((saved) => saved.toLowerCase() === cropName.toLowerCase()) && (
                      <small>{t.savedCrops}</small>
                    )}
                  </button>
                ))}
              </div>
              {selectedCrop && !isTrackedCrop && (
                <button
                  type="button"
                  className="mandi-inline-add"
                  onClick={handleAddViewedCrop}
                  disabled={addingCrop}
                >
                  <Plus size={14} />
                  {addedCrop.toLowerCase() === (selectedCrop || '').toLowerCase() ? t.addedToCrops : t.addToCrops}
                </button>
              )}
            </label>
          </div>
        </section>

        {error && <div className="mandi-error">{error}</div>}

        {!loading && !selectedCrop && (
          <section className="mandi-empty-page">
            <IndianRupee size={34} />
            <p>{t.noCrops}</p>
            <Link to="/dashboard" className="mandi-link-btn">{t.addCrop}</Link>
          </section>
        )}

        {loading && <div className="mandi-loading"><Loader className="mandi-spin" size={18} /> {t.loading}</div>}

        {!loading && selectedCrop && (
          <>
            <section className="mandi-page-grid">
              <article className="mandi-price-card">
                <div className="mandi-card-top">
                  <div>
                    <span className="mandi-label">{t.localPrice}</span>
                    <h3>{primary?.market_name || 'No mandi data'}</h3>
                  </div>
                  <IndianRupee size={20} />
                </div>
                <div className="mandi-location-controls">
                  <label>
                    <span>{t.state}</span>
                    <select
                      value={selectedLocation.state}
                      onChange={(event) => setSelectedLocation({ state: event.target.value, district: '', market: '' })}
                    >
                      <option value="">{t.allStates}</option>
                      {locationStates.map((state) => <option key={state} value={state}>{state}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>{t.district}</span>
                    <select
                      value={selectedLocation.district}
                      onChange={(event) => setSelectedLocation((prev) => ({ ...prev, district: event.target.value, market: '' }))}
                    >
                      <option value="">{t.allDistricts}</option>
                      {locationDistricts.map((district) => <option key={district} value={district}>{district}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>{t.market}</span>
                    <select
                      value={selectedLocation.market}
                      onChange={(event) => {
                        const market = locationMarkets.find((item) => item.market_name === event.target.value);
                        setSelectedLocation((prev) => ({
                          ...prev,
                          market: event.target.value,
                          state: market?.state || prev.state,
                          district: market?.district || prev.district,
                        }));
                      }}
                    >
                      <option value="">{t.selectMarket}</option>
                      {locationMarkets.map((item) => (
                        <option key={`${item.state}-${item.district}-${item.market_name}`} value={item.market_name}>
                          {item.market_name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="mandi-main-price">{formatPrice(primary?.modal_price)}</div>
                <div className="mandi-price-stats">
                  <div><span>{t.min}</span><strong>{formatPrice(primary?.min_price)}</strong></div>
                  <div><span>{t.modal}</span><strong>{formatPrice(primary?.modal_price)}</strong></div>
                  <div><span>{t.max}</span><strong>{formatPrice(primary?.max_price)}</strong></div>
                </div>
                <div className="mandi-meta-row">
                  <span><MapPin size={14} />{primary?.district || primary?.state || 'India'}</span>
                  <span>{formatDate(primary?.price_date)}</span>
                </div>
                <div className="mandi-range-row">
                  <span>{t.stateAvg} {formatPrice(current?.state_summary?.modal_price)}</span>
                  <span>{t.indiaAvg} {formatPrice(current?.india_summary?.modal_price)}</span>
                </div>
                {primary?.data_status !== 'available' && <p className="mandi-muted">{primary?.data_status}</p>}
              </article>

              <article className="mandi-detail-card">
                <div className="mandi-detail-title">
                  <Navigation size={18} />
                  <h3>{t.worthTrip}</h3>
                </div>
                <p className="mandi-context-note">
                  {t.basedOnFarm}{selectedFarm?.location ? `: ${selectedFarm.location}` : ''}.
                </p>
                {comparison?.recommendations?.length ? (
                  <div className="mandi-trip-list">
                    {comparison.recommendations.map((item, index) => (
                      <div className="mandi-trip-item" key={`${item.market_name}-${item.net_gain}`}>
                        <div>
                          <strong>{index + 1}. {item.market_name}</strong>
                          <span>{item.distance_km} km - {formatPrice(item.modal_price)}</span>
                        </div>
                        <div className="mandi-net-gain">
                          <ArrowUpRight size={16} />
                          {formatMoney(item.net_gain)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mandi-muted">{t.noTrip}</p>
                )}
              </article>
            </section>

            <section className="mandi-page-grid">
              <article className="mandi-detail-card">
                <div className="mandi-trend-head">
                  <div className="mandi-detail-title">
                    <TrendIcon size={18} />
                    <div>
                      <h3>{t.trend}</h3>
                      <span>{trendRange}</span>
                    </div>
                  </div>
                  <div className={`mandi-trend-pill ${trend?.direction || 'no_data'}`}>
                    <span>{trend?.direction || 'no_data'}</span>
                    <strong>{trend?.change_pct !== null && trend?.change_pct !== undefined ? `${trend.change_pct}%` : 'No change'}</strong>
                  </div>
                </div>
                <Sparkline points={trend?.points || []} />
                {trendWhy && (
                  <p className="mandi-trend-why">
                    <RefreshCcw size={14} />
                    <span>
                      {t.trendWhy}{' '}
                      <a href={`#news-${trendWhy.id || encodeURIComponent(trendWhy.headline)}`}>
                        {trendWhy.headline}
                      </a>
                      .
                    </span>
                  </p>
                )}
              </article>

              <article className="mandi-detail-card">
                <div className="mandi-detail-title">
                  <Newspaper size={18} />
                  <h3>{t.news}</h3>
                </div>
                {news?.insights?.length ? (
                  <div className="mandi-news-list">
                    {news.insights.slice(0, 5).map((item) => (
                      <article className="mandi-news-card" id={`news-${item.id || encodeURIComponent(item.headline)}`} key={item.id || item.headline}>
                        <h4>{item.headline}</h4>
                        <p>{item.summary}</p>
                        {item.source_url && (
                          <a href={item.source_url} target="_blank" rel="noreferrer">
                            Source <ExternalLink size={12} />
                          </a>
                        )}
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="mandi-muted">{t.noNews}</p>
                )}
              </article>
            </section>
          </>
        )}
      </main>
    </div>
  );
};

export default MandiPrices;
