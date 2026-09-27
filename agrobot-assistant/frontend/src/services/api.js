import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

class ApiService {
  // Authentication endpoints
  async signup(userData) {
    const response = await api.post('/auth/signup', userData);
    return response.data;
  }

  async login(credentials) {
    const params = new URLSearchParams();
    params.append('username', credentials.email);
    params.append('password', credentials.password);

    const response = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  }

  async updatePreferredLanguage(preferredLanguage) {
    const response = await api.patch('/users/me/language', {
      preferred_language: preferredLanguage
    });
    return response.data;
  }

  async transcribeVoice(blob) {
    const formData = new FormData();
    formData.append('audio', blob, 'voice.webm');
    const response = await api.post('/voice/transcribe', formData);
    return response.data;
  }

  // Questionnaire endpoints
  async submitQuestionnaireSet(setNumber, answers, userId, farmId) {
    const response = await api.post('/questionnaire/submit-set', {
      user_id: userId,
      farm_id: farmId,
      set_number: setNumber,
      answers: answers
    });
    return response.data;
  }

  async completeQuestionnaire(questionnaireData) {
    const response = await api.post('/questionnaire/complete', questionnaireData);
    return response.data;
  }

  async getUserQuestionnaireResponses(farmId) {
    const response = await api.get('/questionnaire/user-responses', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getFarms() {
    const response = await api.get('/farms');
    return response.data;
  }

  async createFarm(farmData) {
    const response = await api.post('/farms', farmData);
    return response.data;
  }

  // Recommendations endpoints
  async generateRecommendations(farmId) {
    try {
      const response = await api.post('/recommendations/generate', null, {
        params: farmId ? { farm_id: farmId } : {}
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async refreshRecommendations(farmId) {
    const response = await api.post('/recommendations/refresh', null, {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getLatestRecommendations(farmId) {
    try {
      const response = await api.get('/recommendations/latest', {
        params: farmId ? { farm_id: farmId } : {}
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getRecommendationHistory(farmId) {
    const response = await api.get('/recommendations/history', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getGovernmentSchemes(farmId) {
    const response = await api.get('/recommendations/government-schemes', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async predictDiseaseImage(file, farmId) {
    const formData = new FormData();
    formData.append('image', file);

    const response = await api.post('/disease/predict', formData, {
      params: farmId ? { farm_id: farmId } : {}
    });

    return response.data;
  }

  async getDiseaseHistory(farmId) {
    const response = await api.get('/disease/history', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getFarmCrops(farmId) {
    const response = await api.get('/dashboard/crops', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async createFarmCrop(cropData) {
    const response = await api.post('/dashboard/crops', cropData);
    return response.data;
  }

  async updateFarmCrop(cropId, cropData) {
    const response = await api.patch(`/dashboard/crops/${cropId}`, cropData);
    return response.data;
  }

  async removeFarmCrop(cropId) {
    const response = await api.delete(`/dashboard/crops/${cropId}`);
    return response.data;
  }

  // Weather endpoints (if you add them later)
  async getWeatherData(location) {
    const response = await api.get(`/weather?location=${encodeURIComponent(location)}`);
    return response.data;
  }

  async getWeatherOverview(farmId) {
    const response = await api.get('/weather/overview', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getMandiCurrent(farmId, crop, location = {}, timeout = 30000) {
    const response = await api.get('/mandi-prices/current', {
      timeout,
      params: {
        farm_id: farmId,
        crop,
        market: location.market || undefined,
        state: location.state || undefined,
        district: location.district || undefined,
      }
    });
    return response.data;
  }

  async compareMandiPrices(farmId, crop, radiusKm = 250) {
    const response = await api.get('/mandi-prices/compare', {
      params: { farm_id: farmId, crop, radius_km: radiusKm }
    });
    return response.data;
  }

  async getMandiTrend(market, crop, days = 30) {
    const response = await api.get('/mandi-prices/trend', {
      params: { market, crop, days }
    });
    return response.data;
  }

  async getMandiNews(crop) {
    const response = await api.get('/mandi-prices/news', {
      params: { crop }
    });
    return response.data;
  }

  async getMandiLocations(filters = {}) {
    const response = await api.get('/mandi-prices/locations', {
      params: filters
    });
    return response.data;
  }

  async searchMandiCommodities(q = '') {
    const response = await api.get('/mandi-prices/commodities', {
      params: { q }
    });
    return response.data;
  }

  async getAnalyticsOverview(farmId) {
    const response = await api.get('/analytics/overview', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async getAdvisorFarmers() {
    const response = await api.get('/advisor/farmers');
    return response.data;
  }

  async getAdvisorFarmerSummary(farmerId) {
    const response = await api.get(`/advisor/farmers/${farmerId}/summary`);
    return response.data;
  }

  async saveScheme(schemeId, payload) {
    const response = await api.post(`/schemes/${schemeId}/save`, payload);
    return response.data;
  }

  async getSchemeRecords(farmId) {
    const response = await api.get('/schemes/records', {
      params: farmId ? { farm_id: farmId } : {}
    });
    return response.data;
  }

  async updateSchemeRecord(recordId, payload) {
    const response = await api.patch(`/schemes/records/${recordId}`, payload);
    return response.data;
  }

}

// eslint-disable-next-line import/no-anonymous-default-export
const apiService = new ApiService();

export default apiService;
