import React from 'react';
import { Link } from 'react-router-dom';
import {
  Sprout, Camera, IndianRupee, Landmark, CloudSun, BarChart3,
  ArrowRight, Droplets, Search, HelpCircle, ChevronDown,
} from 'lucide-react';
import usePageMeta from '../hooks/usePageMeta';
import './Home.css';

const ICON = { strokeWidth: 2.75 };

const FEATURES = [
  {
    Icon: Sprout,
    tone: 'sage',
    title: 'Crop recommendations for your soil',
    body: 'Tell us your soil type, water source and season. AgroBot ranks the crops that suit your land and explains why.',
    cta: 'Get crop advice',
    to: '/signup',
  },
  {
    Icon: Camera,
    tone: 'terra',
    title: 'Plant disease check from a leaf photo',
    body: 'Photograph one leaf. AgroBot names the likely disease, shows how sure it is, and suggests a treatment you can buy locally.',
    cta: 'Check a leaf',
    to: '/disease-checkup',
  },
  {
    Icon: IndianRupee,
    tone: 'sage',
    title: "Today's mandi prices",
    body: 'See min, modal and max prices from Agmarknet, the 30-day trend, and whether a farther mandi is worth the trip.',
    cta: 'See mandi prices',
    to: '/mandi-prices',
  },
  {
    Icon: Landmark,
    tone: 'terra',
    title: 'Government schemes you qualify for',
    body: 'Match your state, crop and farm size to schemes like PM-KISAN and Per Drop More Crop, with a documents checklist.',
    cta: 'Find schemes',
    to: '/government-schemes',
  },
  {
    Icon: CloudSun,
    tone: 'sage',
    title: 'Weather and irrigation advice',
    body: 'A three-day forecast for your village, and a plain answer to “should I water today?”',
    cta: 'See the forecast',
    to: '/dashboard',
  },
  {
    Icon: BarChart3,
    tone: 'terra',
    title: 'Farm history and reports',
    body: 'Track your soil score, crop mix and disease checks over time, and share a report with your advisor.',
    cta: 'View a sample report',
    to: '/analytics',
  },
];

const STEPS = [
  {
    n: '1',
    title: 'Tell us about your farm',
    body: 'Five short steps about soil, water, weather and how you farm. Voice answers and “Don’t know” are always allowed.',
  },
  {
    n: '2',
    title: 'Get today’s plan',
    body: 'A short list of what to do on your farm today, with the reason for each and the crops that suit your land.',
  },
  {
    n: '3',
    title: 'Check a leaf, a price or a scheme',
    body: 'Use the tools whenever you need them. Every answer shows where it came from.',
  },
];

const FAQS = [
  {
    q: 'Which languages does AgroBot support?',
    a: 'English and Hindi (हिंदी). You can switch language on any screen, and your choice is remembered across the whole app.',
  },
  {
    q: 'How does the plant disease check work?',
    a: 'Take a clear photo of a single leaf in daylight, or upload a JPG or PNG up to 10 MB. AgroBot names the likely disease, shows how confident it is, and suggests a cause and treatment. If the photo is unclear, it tells you instead of guessing.',
  },
  {
    q: 'Where do the mandi prices come from?',
    a: 'Prices come from Agmarknet, the Government of India’s agricultural marketing network. AgroBot shows the minimum, modal and maximum price per quintal and the date of each price.',
  },
  {
    q: 'How does AgroBot recommend crops?',
    a: 'A machine-learning model compares your farm’s soil, water and climate against 22 trained crop classes, checked against a verified crop knowledge base. Every recommendation shows how reliable its data is and what it could not verify.',
  },
  {
    q: 'Do I need a soil test?',
    a: 'No. Without a soil test, AgroBot uses regional averages and clearly labels those values as estimated. Adding soil-test values later makes the recommendation more reliable.',
  },
  {
    q: 'Can AgroBot apply for government schemes for me?',
    a: 'No. AgroBot finds schemes that match your state, crop and farm size, lists the documents you need, and links you to the official portal to apply.',
  },
];

const SAMPLE_TASKS = [
  { Icon: Droplets, tone: 'sage', title: 'Hold irrigation', note: '72% chance of rain tomorrow — wait two days.' },
  { Icon: Sprout, tone: 'terra', title: 'Top-dress the soybean plot', note: 'Second split of nitrogen is due this week.' },
  { Icon: Search, tone: 'neutral', title: 'Scout onion rows for leaf miner', note: 'Check the undersides of older leaves.' },
];

const Home = () => {
  usePageMeta({
    title: 'AgroBot – AI Farming Assistant for Indian Farmers',
    description: "AgroBot is an AI farming assistant for Indian farmers. Get crop recommendations for your soil, check plant disease from a leaf photo, see today's mandi prices and find government schemes — in English and हिंदी.",
    path: '/',
  });

  return (
    <div className="home">
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="site-header">
        <nav className="site-nav page-wrap" aria-label="Main">
          <Link to="/" className="site-brand" aria-label="AgroBot home">
            <span className="site-brand-mark"><Sprout size={20} {...ICON} /></span>
            AgroBot
          </Link>
          <div className="site-nav-links">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#faq">Questions</a>
          </div>
          <div className="site-nav-actions">
            <Link to="/login" className="btn btn-secondary">Log in</Link>
            <Link to="/signup" className="btn btn-primary">Get started</Link>
          </div>
        </nav>
      </header>

      <main id="main">
        {/* ── hero ── */}
        <section className="hero page-wrap" aria-labelledby="hero-title">
          <div className="hero-blob" aria-hidden="true" />
          <div className="hero-grid">
            <div>
              <h1 id="hero-title" className="hero-title">
                <span>Know what your farm</span>
                <span>needs today.</span>
              </h1>
              <p className="hero-lede">
                AgroBot is an AI farming assistant for Indian farmers. It turns your soil, weather and
                crops into a short list of things to do today — crop advice, a leaf disease check,
                mandi prices and government schemes, in English and हिंदी.
              </p>
              <div className="hero-actions">
                <Link to="/signup" className="btn btn-primary btn-lg">
                  Get started <ArrowRight size={18} {...ICON} />
                </Link>
                <Link to="/dashboard" className="btn btn-secondary btn-lg">See a sample farm</Link>
              </div>
              <p className="hero-note">Works on any phone browser. No soil test needed to start.</p>
            </div>

            <figure className="hero-figure">
              <div className="card card-raised elev-lg hero-card">
                <div className="hero-card-head">
                  <p className="hero-card-title">Today on your farm</p>
                  <span className="tag tag-neutral">Sat 27 Sep</span>
                </div>
                <div className="hero-task-list">
                  {SAMPLE_TASKS.map((task) => (
                    <div key={task.title} className="hero-task">
                      <span className={`hero-task-icon ${task.tone}`}><task.Icon size={20} {...ICON} /></span>
                      <div>
                        <p className="hero-task-title">{task.title}</p>
                        <p className="hero-task-note">{task.note}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="hero-card-foot">
                  <span className="text-muted">Soil moisture</span>
                  <span className="tag tag-unknown"><HelpCircle size={14} {...ICON} /> Not assessed</span>
                </div>
              </div>
              <figcaption>A sample day for a soybean and onion farm near Nashik, Maharashtra.</figcaption>
            </figure>
          </div>
        </section>

        {/* ── features ── */}
        <section id="features" className="section page-wrap" aria-labelledby="features-title">
          <h2 id="features-title" className="section-title">Six farm tools, one simple app</h2>
          <p className="section-lede">
            Every tool starts from your own farm profile, so answers fit your soil, your district and
            your season.
          </p>
          <div className="feature-grid">
            {FEATURES.map((feature) => (
              <article key={feature.title} className="card feature-card">
                <span className={`feature-icon ${feature.tone}`}><feature.Icon size={24} {...ICON} /></span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
                <Link to={feature.to} className="feature-link">
                  {feature.cta} <ArrowRight size={16} {...ICON} />
                </Link>
              </article>
            ))}
          </div>
        </section>

        {/* ── honesty ── */}
        <section className="section page-wrap" aria-labelledby="honest-title">
          <div className="honest-grid">
            <div>
              <h2 id="honest-title" className="section-title">It tells you what it doesn’t know</h2>
              <p className="section-lede">
                AgroBot never makes up a number. When a value is missing it says <strong>Not assessed</strong>.
                When it uses a regional average instead of your soil test, it says <strong>estimated</strong>.
                When it can’t check something, it tells you what, and what to add next.
              </p>
              <p className="section-lede">
                So you know which advice is solid, and which needs one more detail from you.
              </p>
            </div>
            <article className="card card-raised elev-md honest-card" aria-label="Example crop recommendation">
              <div className="honest-card-head">
                <span className="crop-rank">1</span>
                <p className="honest-card-title">Soybean</p>
              </div>
              <span className="tag tag-good">High suitability</span>
              <p><strong>Next:</strong> Confirm seed treatment before sowing.</p>
              <div className="honest-card-tags">
                <span className="tag tag-neutral">6 checks verified</span>
                <span className="tag tag-unknown">Could not verify: rainfall</span>
              </div>
              <p className="text-muted honest-card-meta">
                Source: ML model + crop knowledge · Data reliability: medium
              </p>
            </article>
          </div>
        </section>

        {/* ── how it works ── */}
        <section id="how" className="section page-wrap" aria-labelledby="how-title">
          <h2 id="how-title" className="section-title">How AgroBot works</h2>
          <ol className="step-grid">
            {STEPS.map((step) => (
              <li key={step.n} className="card step-card">
                <span className="step-number" aria-hidden="true">{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* ── faq ── */}
        <section id="faq" className="section page-wrap" aria-labelledby="faq-title">
          <h2 id="faq-title" className="section-title">Questions farmers ask</h2>
          <div className="faq-list">
            {FAQS.map((faq) => (
              <details key={faq.q} className="card faq-item">
                <summary>
                  <h3>{faq.q}</h3>
                  <ChevronDown size={22} className="chev" {...ICON} />
                </summary>
                <p>{faq.a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* ── closing CTA ── */}
        <section className="section page-wrap" aria-labelledby="close-title">
          <div className="cta-band">
            <h2 id="close-title">Set up your farm in five short steps</h2>
            <p>Start monitoring your crops and get today’s plan. No soil test needed.</p>
            <Link to="/signup" className="btn btn-primary btn-lg">
              Get started <ArrowRight size={18} {...ICON} />
            </Link>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="page-wrap site-footer-top">
          <span className="site-footer-brand">AgroBot</span>
          <Link to="/mandi-prices">Mandi prices</Link>
          <Link to="/government-schemes">Schemes</Link>
          <Link to="/disease-checkup">Disease check</Link>
          <Link to="/analytics">Farm history</Link>
          <a href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer noopener">myScheme</a>
          <a href="https://agmarknet.gov.in/" target="_blank" rel="noreferrer noopener">Agmarknet</a>
        </div>
        <div className="page-wrap site-footer-bottom">
          <span>© 2026 AgroBot · MIT licensed</span>
          <a href="mailto:udayparmar21014002@gmail.com">Contact</a>
        </div>
      </footer>
    </div>
  );
};

export default Home;
