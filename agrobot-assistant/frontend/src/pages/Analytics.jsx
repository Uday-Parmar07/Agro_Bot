import React, { useState } from 'react';
import { BarChart3, TrendingUp, PieChart, Activity, Calendar, Download } from 'lucide-react';
import './Analytics.css';

const Analytics = () => {
  const [timeRange, setTimeRange] = useState('30d');

  const analyticsData = {
    overview: {
      totalYield: '2,450 kg',
      yieldChange: '+12%',
      waterUsage: '15,240 L',
      waterChange: '-8%',
      efficiency: '87%',
      efficiencyChange: '+5%',
      revenue: '$12,450',
      revenueChange: '+15%'
    },
    cropPerformance: [
      { crop: 'Tomatoes', yield: 850, target: 800, efficiency: 106 },
      { crop: 'Corn', yield: 720, target: 750, efficiency: 96 },
      { crop: 'Wheat', yield: 680, target: 650, efficiency: 105 },
      { crop: 'Soybeans', yield: 200, target: 180, efficiency: 111 }
    ],
    monthlyTrends: [
      { month: 'Jan', yield: 1200, water: 8500, efficiency: 82 },
      { month: 'Feb', yield: 1350, water: 9200, efficiency: 84 },
      { month: 'Mar', yield: 1580, water: 10100, efficiency: 86 },
      { month: 'Apr', yield: 1820, water: 11800, efficiency: 87 },
      { month: 'May', yield: 2100, water: 13200, efficiency: 89 },
      { month: 'Jun', yield: 2450, water: 15240, efficiency: 87 }
    ]
  };

  const timeRanges = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: '1y', label: '1 Year' }
  ];

  return (
    <div className="analytics-page">
      <div className="analytics-container">
        <header className="analytics-header">
          <div className="header-content">
            <h1>Farm Analytics</h1>
            <p>Comprehensive insights into your agricultural operations and performance metrics</p>
          </div>
          <div className="header-controls">
            <div className="time-range-selector">
              {timeRanges.map(range => (
                <button
                  key={range.value}
                  className={`time-btn ${timeRange === range.value ? 'active' : ''}`}
                  onClick={() => setTimeRange(range.value)}
                >
                  {range.label}
                </button>
              ))}
            </div>
            <button className="btn btn-primary">
              <Download size={16} />
              Export Report
            </button>
          </div>
        </header>

        <div className="analytics-overview">
          <div className="overview-card">
            <div className="card-header">
              <h3>Total Yield</h3>
              <TrendingUp className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.totalYield}</div>
            <div className="card-change positive">{analyticsData.overview.yieldChange} from last period</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Water Usage</h3>
              <Activity className="card-icon negative" />
            </div>
            <div className="card-value">{analyticsData.overview.waterUsage}</div>
            <div className="card-change negative">{analyticsData.overview.waterChange} from last period</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Efficiency</h3>
              <BarChart3 className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.efficiency}</div>
            <div className="card-change positive">{analyticsData.overview.efficiencyChange} from last period</div>
          </div>

          <div className="overview-card">
            <div className="card-header">
              <h3>Revenue</h3>
              <PieChart className="card-icon positive" />
            </div>
            <div className="card-value">{analyticsData.overview.revenue}</div>
            <div className="card-change positive">{analyticsData.overview.revenueChange} from last period</div>
          </div>
        </div>

        <div className="analytics-charts">
          <div className="chart-section">
            <div className="chart-header">
              <h2>Crop Performance Analysis</h2>
              <p>Yield performance vs targets for each crop type</p>
            </div>
            <div className="crop-performance-chart">
              {analyticsData.cropPerformance.map((crop, index) => (
                <div key={index} className="crop-bar-item">
                  <div className="crop-info">
                    <span className="crop-name">{crop.crop}</span>
                    <span className="crop-yield">{crop.yield} kg</span>
                  </div>
                  <div className="progress-container">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${(crop.yield / crop.target) * 100}%` }}
                      ></div>
                    </div>
                    <span className="efficiency-badge">
                      {crop.efficiency}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="chart-section">
            <div className="chart-header">
              <h2>Monthly Trends</h2>
              <p>Yield, water usage, and efficiency trends over time</p>
            </div>
            <div className="trends-chart">
              <div className="chart-legend">
                <div className="legend-item">
                  <div className="legend-color yield"></div>
                  <span>Yield (kg)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color water"></div>
                  <span>Water Usage (L)</span>
                </div>
                <div className="legend-item">
                  <div className="legend-color efficiency"></div>
                  <span>Efficiency (%)</span>
                </div>
              </div>
              <div className="chart-grid">
                {analyticsData.monthlyTrends.map((month, index) => (
                  <div key={index} className="chart-column">
                    <div className="chart-bars">
                      <div 
                        className="chart-bar yield"
                        style={{ height: `${(month.yield / 2500) * 100}%` }}
                        title={`Yield: ${month.yield} kg`}
                      ></div>
                      <div 
                        className="chart-bar water"
                        style={{ height: `${(month.water / 16000) * 100}%` }}
                        title={`Water: ${month.water} L`}
                      ></div>
                      <div 
                        className="chart-bar efficiency"
                        style={{ height: `${month.efficiency}%` }}
                        title={`Efficiency: ${month.efficiency}%`}
                      ></div>
                    </div>
                    <span className="chart-label">{month.month}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="insights-section">
          <h2>Key Insights & Recommendations</h2>
          <div className="insights-grid">
            <div className="insight-card">
              <div className="insight-icon positive">
                <TrendingUp size={24} />
              </div>
              <div className="insight-content">
                <h3>Yield Optimization</h3>
                <p>Tomato and soybean crops are performing above target. Consider expanding these crops in the next season.</p>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon warning">
                <Activity size={24} />
              </div>
              <div className="insight-content">
                <h3>Water Efficiency</h3>
                <p>Water usage has decreased by 8% while maintaining yield. Continue current irrigation schedule for optimal efficiency.</p>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon info">
                <BarChart3 size={24} />
              </div>
              <div className="insight-content">
                <h3>Corn Performance</h3>
                <p>Corn yield is slightly below target. Consider soil analysis and nutrient supplementation for improvement.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
