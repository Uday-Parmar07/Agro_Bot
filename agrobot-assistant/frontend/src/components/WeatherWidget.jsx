import React, { useState } from 'react';
import { Cloud, Sun, CloudRain, Wind, Eye, Gauge, Droplets, MapPin } from 'lucide-react';
import './WeatherWidget.css';

const WeatherWidget = () => {
  const [weather] = useState({
    current: {
      temperature: 24,
      condition: 'Partly Cloudy',
      humidity: 68,
      windSpeed: 12,
      visibility: 10,
      pressure: 1013,
      location: 'Farm Location'
    },
    forecast: [
      { day: 'Today', high: 26, low: 18, condition: 'Sunny', icon: '☀️' },
      { day: 'Tomorrow', high: 24, low: 16, condition: 'Cloudy', icon: '☁️' },
      { day: 'Wed', high: 22, low: 14, condition: 'Rainy', icon: '🌧️' }
    ]
  });

  const getWeatherIcon = (condition) => {
    switch (condition.toLowerCase()) {
      case 'sunny': return <Sun className="weather-main-icon sunny" />;
      case 'cloudy': 
      case 'partly cloudy': return <Cloud className="weather-main-icon cloudy" />;
      case 'rainy': return <CloudRain className="weather-main-icon rainy" />;
      default: return <Sun className="weather-main-icon" />;
    }
  };

  return (
    <div className="weather-widget">
      <div className="weather-header">
        <div className="header-title">
          <h2>Weather Conditions</h2>
          <div className="location-info">
            <MapPin size={14} />
            <span>{weather.current.location}</span>
          </div>
        </div>
      </div>

      <div className="current-weather-section">
        <div className="weather-main">
          <div className="weather-icon-container">
            {getWeatherIcon(weather.current.condition)}
          </div>
          <div className="temperature-display">
            <span className="temp-value">{weather.current.temperature}</span>
            <span className="temp-unit">°C</span>
          </div>
        </div>
        <div className="condition-info">
          <span className="condition-text">{weather.current.condition}</span>
        </div>
      </div>

      <div className="weather-metrics">
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon humidity">
              <Droplets size={18} />
            </div>
            <div className="metric-content">
              <span className="metric-label">Humidity</span>
              <span className="metric-value">{weather.current.humidity}%</span>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon wind">
              <Wind size={18} />
            </div>
            <div className="metric-content">
              <span className="metric-label">Wind</span>
              <span className="metric-value">{weather.current.windSpeed} km/h</span>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon visibility">
              <Eye size={18} />
            </div>
            <div className="metric-content">
              <span className="metric-label">Visibility</span>
              <span className="metric-value">{weather.current.visibility} km</span>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon pressure">
              <Gauge size={18} />
            </div>
            <div className="metric-content">
              <span className="metric-label">Pressure</span>
              <span className="metric-value">{weather.current.pressure} hPa</span>
            </div>
          </div>
        </div>
      </div>

      <div className="forecast-section">
        <h3>3-Day Forecast</h3>
        <div className="forecast-cards">
          {weather.forecast.map((day, index) => (
            <div key={index} className="forecast-card">
              <div className="forecast-day">{day.day}</div>
              <div className="forecast-icon">{day.icon}</div>
              <div className="forecast-temps">
                <span className="forecast-high">{day.high}°</span>
                <span className="forecast-low">{day.low}°</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WeatherWidget;
