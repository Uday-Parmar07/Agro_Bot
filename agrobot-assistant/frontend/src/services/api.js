import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
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
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    // Let the browser set multipart boundary automatically.
    const response = await api.post('/auth/login', formData);
    return response.data;
  }

  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  }

  // Questionnaire endpoints
  async submitQuestionnaireSet(setNumber, answers, userId) {
    const response = await api.post('/questionnaire/submit-set', {
      user_id: userId,
      set_number: setNumber,
      answers: answers
    });
    return response.data;
  }

  async completeQuestionnaire(questionnaireData) {
    const response = await api.post('/questionnaire/complete', questionnaireData);
    return response.data;
  }

  async getUserQuestionnaireResponses() {
    const response = await api.get('/questionnaire/user-responses');
    return response.data;
  }

  // Recommendations endpoints
  async generateRecommendations() {
    try {
      console.log('🤖 Calling generate recommendations API...');
      const response = await api.post('/recommendations/generate');
      console.log('✅ Generate recommendations response:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Generate recommendations error:', error);
      console.error('Error response:', error.response?.data);
      throw error;
    }
  }

  async getLatestRecommendations() {
    try {
      console.log('📊 Calling get latest recommendations API...');
      const response = await api.get('/recommendations/latest');
      console.log('✅ Latest recommendations response:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Get latest recommendations error:', error);
      console.error('Error response:', error.response?.data);
      throw error;
    }
  }

  async getRecommendationHistory() {
    const response = await api.get('/recommendations/history');
    return response.data;
  }

  async getGovernmentSchemes() {
    const response = await api.get('/recommendations/government-schemes');
    return response.data;
  }

  async predictDiseaseImage(file) {
    const formData = new FormData();
    formData.append('image', file);

    const response = await api.post('/disease/predict', formData);

    return response.data;
  }

  // Weather endpoints (if you add them later)
  async getWeatherData(location) {
    const response = await api.get(`/weather?location=${encodeURIComponent(location)}`);
    return response.data;
  }

  async getWeatherOverview() {
    const response = await api.get('/weather/overview');
    return response.data;
  }
}

export default new ApiService();
