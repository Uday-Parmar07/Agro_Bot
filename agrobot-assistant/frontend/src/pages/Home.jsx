import React from 'react';
import { Link } from 'react-router-dom';
import { Leaf, BarChart3, Cloud, ArrowRight, CheckCircle, Zap } from 'lucide-react';
import './Home.css';

const Home = () => {
  const features = [
    {
      icon: <Leaf className="feature-icon" />,
      title: "Real-time Crop Monitoring",
      description: "Monitor crop health, soil moisture, and temperature with live sensor data and AI-powered insights."
    },
    {
      icon: <Cloud className="feature-icon" />,
      title: "Weather Intelligence",
      description: "Get accurate weather forecasts and alerts to make informed decisions about irrigation and harvesting."
    },
    {
      icon: <BarChart3 className="feature-icon" />,
      title: "Analytics & Insights",
      description: "Analyze historical data, predict yields, and optimize farming operations with advanced analytics."
    }
  ];

  const benefits = [
    "Increase crop yield by up to 25%",
    "Reduce water usage by 30%",
    "Early disease detection and prevention",
    "Optimize fertilizer and pesticide usage",
    "Real-time alerts and notifications",
    "Historical data analysis and reporting"
  ];

  return (
    <div className="home">
      <header className="hero-section">
        <div className="container">
          <div className="hero-content">
            <div className="hero-text">
              <h1 className="hero-title">
                Smart Agriculture with
                <span className="gradient-text"> AI-Powered Insights</span>
              </h1>
              <p className="hero-subtitle">
                Transform your farming operations with real-time monitoring, predictive analytics, 
                and intelligent recommendations. Make data-driven decisions that maximize yield 
                and optimize resource usage.
              </p>
              <div className="hero-actions">
                <Link to="/signup" className="btn btn-primary">
                  <Zap size={20} />
                  Get Started
                </Link>
                <Link to="/analytics" className="btn btn-secondary">
                  View Demo
                  <ArrowRight size={20} />
                </Link>
              </div>
            </div>
            <div className="hero-visual">
              <div className="dashboard-preview">
                <div className="preview-header">
                  <div className="preview-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="preview-title">AgroBot Dashboard</span>
                </div>
                <div className="preview-content">
                  <div className="preview-stats">
                    <div className="stat-item">
                      <Leaf size={16} />
                      <span>12 Active Fields</span>
                    </div>
                    <div className="stat-item">
                      <Cloud size={16} />
                      <span>24°C Optimal</span>
                    </div>
                  </div>
                  <div className="preview-chart">
                    <div className="chart-bars">
                      <div className="bar" style={{height: '60%'}}></div>
                      <div className="bar" style={{height: '80%'}}></div>
                      <div className="bar" style={{height: '45%'}}></div>
                      <div className="bar" style={{height: '90%'}}></div>
                      <div className="bar" style={{height: '70%'}}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <section className="features-section">
        <div className="container">
          <div className="section-header">
            <h2>Comprehensive Farm Management</h2>
            <p>Everything you need to monitor and optimize your agricultural operations</p>
          </div>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon-wrapper">
                  {feature.icon}
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="benefits-section">
        <div className="container">
          <div className="benefits-content">
            <div className="benefits-text">
              <h2>Why Choose AgroBot?</h2>
              <p>
                Our AI-powered agricultural dashboard helps farmers and agricultural analysts 
                make smarter decisions with real-time data and predictive insights.
              </p>
              <div className="benefits-list">
                {benefits.map((benefit, index) => (
                  <div key={index} className="benefit-item">
                    <CheckCircle className="check-icon" />
                    <span>{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="benefits-visual">
              <div className="stats-showcase">
                <div className="showcase-stat">
                  <span className="stat-number">25%</span>
                  <span className="stat-label">Yield Increase</span>
                </div>
                <div className="showcase-stat">
                  <span className="stat-number">30%</span>
                  <span className="stat-label">Water Savings</span>
                </div>
                <div className="showcase-stat">
                  <span className="stat-number">24/7</span>
                  <span className="stat-label">Monitoring</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2>Ready to Transform Your Farm?</h2>
            <p>Start monitoring your crops and optimizing your operations today</p>
            <Link to="/dashboard" className="btn btn-primary btn-large">
              Get Started Now
              <ArrowRight size={20} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
