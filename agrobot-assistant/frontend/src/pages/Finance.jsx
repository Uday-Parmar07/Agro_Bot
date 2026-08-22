import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import './FeaturePages.css';

const emi = (principal, annualRate, months, subsidy) => {
  const effectivePrincipal = principal * (1 - subsidy / 100);
  const r = annualRate / 12 / 100;
  if (!months) return 0;
  if (!r) return effectivePrincipal / months;
  return effectivePrincipal * r * ((1 + r) ** months) / (((1 + r) ** months) - 1);
};

const Finance = () => {
  const [farms, setFarms] = useState([]);
  const [farmId, setFarmId] = useState(null);
  const [records, setRecords] = useState([]);
  const [crops, setCrops] = useState([]);
  const [profitability, setProfitability] = useState(null);
  const [loan, setLoan] = useState({ principal: 100000, rate: 8, months: 24, subsidy: 20 });
  const [harvest, setHarvest] = useState({ farm_crop_id: '', actual_yield: '', unit: 'kg', sale_price_per_unit: '', harvested_at: '' });

  useEffect(() => {
    ApiService.getFarms().then((items) => {
      setFarms(items);
      setFarmId(items[0]?.id || null);
    });
  }, []);

  useEffect(() => {
    if (!farmId) return;
    ApiService.getSchemeRecords(farmId).then(setRecords);
    ApiService.getFarmCrops(farmId).then(setCrops);
    ApiService.getProfitability(farmId).then(setProfitability);
  }, [farmId]);

  const monthlyEmi = useMemo(() => emi(Number(loan.principal), Number(loan.rate), Number(loan.months), Number(loan.subsidy)), [loan]);

  const saveHarvest = async (event) => {
    event.preventDefault();
    await ApiService.createHarvestOutcome({
      ...harvest,
      farm_crop_id: Number(harvest.farm_crop_id),
      actual_yield: Number(harvest.actual_yield),
      sale_price_per_unit: Number(harvest.sale_price_per_unit),
    });
    setProfitability(await ApiService.getProfitability(farmId));
  };

  return (
    <div className="feature-page">
      <div className="feature-container">
        <header className="feature-header">
          <div><h1>Financial Tools</h1><p>Track schemes, calculate EMI, and log harvest outcomes.</p></div>
          <Link className="feature-button secondary" to="/dashboard">Dashboard</Link>
        </header>
        {farms.length > 1 && <select value={farmId || ''} onChange={(e) => setFarmId(Number(e.target.value))}>{farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}</select>}
        <section className="feature-grid">
          <form className="feature-form">
            <h2>Loan Calculator</h2>
            <input type="number" value={loan.principal} onChange={(e) => setLoan({ ...loan, principal: e.target.value })} placeholder="Principal" />
            <input type="number" value={loan.rate} onChange={(e) => setLoan({ ...loan, rate: e.target.value })} placeholder="Annual interest %" />
            <input type="number" value={loan.months} onChange={(e) => setLoan({ ...loan, months: e.target.value })} placeholder="Months" />
            <input type="number" value={loan.subsidy} onChange={(e) => setLoan({ ...loan, subsidy: e.target.value })} placeholder="Subsidy %" />
            <strong>Estimated EMI: ₹{monthlyEmi.toFixed(2)}</strong>
          </form>
          <form className="feature-form" onSubmit={saveHarvest}>
            <h2>Harvest Outcome</h2>
            <select value={harvest.farm_crop_id} onChange={(e) => setHarvest({ ...harvest, farm_crop_id: e.target.value })} required>
              <option value="">Select crop</option>
              {crops.map((crop) => <option key={crop.id} value={crop.id}>{crop.crop_name}</option>)}
            </select>
            <input type="number" value={harvest.actual_yield} onChange={(e) => setHarvest({ ...harvest, actual_yield: e.target.value })} placeholder="Actual yield" required />
            <input value={harvest.unit} onChange={(e) => setHarvest({ ...harvest, unit: e.target.value })} placeholder="Unit" required />
            <input type="number" value={harvest.sale_price_per_unit} onChange={(e) => setHarvest({ ...harvest, sale_price_per_unit: e.target.value })} placeholder="Sale price per unit" required />
            <input type="date" value={harvest.harvested_at} onChange={(e) => setHarvest({ ...harvest, harvested_at: e.target.value })} required />
            <button className="feature-button">Log Harvest</button>
          </form>
        </section>
        <section className="feature-grid">
          <article className="feature-card"><h3>Tracked Schemes</h3>{records.map((record) => <p key={record.id}>{record.scheme_name} - {record.status}</p>)}{!records.length && <p>No saved schemes yet.</p>}</article>
          <article className="feature-card"><h3>Profitability</h3>{profitability?.outcomes?.map((item, idx) => <p key={idx}>{item.crop_name}: ₹{item.realized_revenue}</p>)}{!profitability?.outcomes?.length && <p>No harvest outcomes yet.</p>}</article>
        </section>
      </div>
    </div>
  );
};

export default Finance;
