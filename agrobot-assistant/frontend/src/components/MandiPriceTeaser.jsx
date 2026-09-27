import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { IndianRupee, TrendingDown, TrendingUp } from 'lucide-react';
import ApiService from '../services/api';
import './MandiPrices.css';

const formatPrice = (value) => {
  if (value === null || value === undefined) return 'No data';
  return `Rs. ${Number(value).toLocaleString('en-IN')}/q`;
};

const MandiPriceTeaser = ({ farmId, crops, onAddCrop }) => {
  const firstCrop = useMemo(() => crops.find((crop) => crop.name), [crops]);
  const [current, setCurrent] = useState(null);
  const [trend, setTrend] = useState(null);
  const [loading, setLoading] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!farmId || !firstCrop?.name) {
      setCurrent(null);
      setTrend(null);
      setUnavailable(false);
      return;
    }

    let cancelled = false;
    const loadTeaser = async () => {
      setLoading(true);
      setUnavailable(false);
      try {
        const price = await ApiService.getMandiCurrent(farmId, firstCrop.name, {}, 8000);
        if (cancelled) return;
        setCurrent(price);
        const market = price.primary_market || price.nearby?.[0]?.market_name;
        if (market) {
          const trendResult = await ApiService.getMandiTrend(market, firstCrop.name, 30).catch(() => null);
          if (!cancelled) setTrend(trendResult);
        }
      } catch (_error) {
        if (!cancelled) {
          setCurrent(null);
          setTrend(null);
          setUnavailable(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadTeaser();
    return () => {
      cancelled = true;
    };
  }, [farmId, firstCrop?.name]);

  const primary = current?.nearby?.find((item) => item.modal_price !== null && item.modal_price !== undefined) || current?.nearby?.[0];
  const TrendIcon = trend?.direction === 'down' ? TrendingDown : TrendingUp;

  return (
    <section className="mandi-panel mandi-teaser">
      <div className="mandi-panel-header">
        <div>
          <h2>Mandi Prices</h2>
          <p>Local price and trend at a glance.</p>
        </div>
        {firstCrop ? (
          <Link className="mandi-link-btn" to="/mandi-prices">View full mandi prices</Link>
        ) : (
          <button className="mandi-add-crop-btn" onClick={onAddCrop}>Add Crop</button>
        )}
      </div>

      {!firstCrop ? (
        <p className="mandi-muted">Add a crop to check nearby market prices.</p>
      ) : loading ? (
        <div className="mandi-loading">Loading mandi prices...</div>
      ) : unavailable ? (
        <p className="mandi-muted">Market prices are temporarily unavailable. Crop recommendations are unaffected.</p>
      ) : (
        <div className="mandi-teaser-row">
          <div className="mandi-teaser-price">
            <IndianRupee size={18} />
            <div>
              <span>{firstCrop.name}</span>
              <strong>{formatPrice(primary?.modal_price)}</strong>
              <small>{primary?.market_name || 'No recent mandi data'}</small>
            </div>
          </div>
          <div className={`mandi-teaser-trend ${trend?.direction || 'no_data'}`}>
            <TrendIcon size={18} />
            <span>{trend?.direction || 'no_data'}</span>
          </div>
        </div>
      )}
    </section>
  );
};

export default MandiPriceTeaser;
