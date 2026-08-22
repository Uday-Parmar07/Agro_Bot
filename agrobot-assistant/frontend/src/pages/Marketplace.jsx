import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import './FeaturePages.css';

const Marketplace = () => {
  const [listings, setListings] = useState([]);
  const [form, setForm] = useState({ crop_name: '', quantity: '', unit: 'kg', price: '', location: '', contact_pref: '' });

  const load = () => ApiService.getListings().then(setListings);
  useEffect(() => { load(); }, []);

  const submit = async (event) => {
    event.preventDefault();
    await ApiService.createListing({ ...form, quantity: Number(form.quantity), price: Number(form.price) });
    setForm({ crop_name: '', quantity: '', unit: 'kg', price: '', location: '', contact_pref: '' });
    load();
  };

  return (
    <div className="feature-page"><div className="feature-container">
      <header className="feature-header"><div><h1>Marketplace</h1><p>List surplus produce and browse active listings.</p></div><Link className="feature-button secondary" to="/dashboard">Dashboard</Link></header>
      <form className="feature-form" onSubmit={submit}>
        <h2>Create Listing</h2>
        <input value={form.crop_name} onChange={(e) => setForm({ ...form, crop_name: e.target.value })} placeholder="Crop name" required />
        <input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} placeholder="Quantity" required />
        <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="Unit" required />
        <input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="Price" required />
        <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Location" />
        <input value={form.contact_pref} onChange={(e) => setForm({ ...form, contact_pref: e.target.value })} placeholder="Contact preference" />
        <button className="feature-button">Publish</button>
      </form>
      <section className="feature-grid">{listings.map((listing) => <article className="feature-card" key={listing.id}><h3>{listing.crop_name}</h3><p>{listing.quantity} {listing.unit} at ₹{listing.price}</p><p>{listing.location}</p><p>{listing.contact_pref}</p><button className="feature-button secondary" onClick={() => ApiService.reportContent({ target_type: 'listing', target_id: listing.id, reason: 'Needs review' })}>Report</button></article>)}</section>
    </div></div>
  );
};

export default Marketplace;
