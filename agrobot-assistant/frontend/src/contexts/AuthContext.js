import React, { createContext, useContext, useState, useEffect } from 'react';
import ApiService from '../services/api';
import i18n from '../i18n';

const AuthContext = createContext();

// FastAPI validation errors (422) return `detail` as a list of objects, which
// React cannot render; fall back to the first message or a generic one.
const errorMessage = (error, fallback) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg;
  return fallback;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user');

      if (token && savedUser) {
        // Use cached user immediately — no spinner, no blocking network call
        try {
          const parsed = JSON.parse(savedUser);
          setUser(parsed);
          setIsAuthenticated(true);
          if (parsed.preferred_language) i18n.changeLanguage(parsed.preferred_language);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
        }
        setLoading(false);

        // Validate token in the background; update or logout silently
        try {
          const userData = await ApiService.getCurrentUser();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
          localStorage.setItem('preferred_language', userData.preferred_language || 'en');
          i18n.changeLanguage(userData.preferred_language || 'en');
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          setUser(null);
          setIsAuthenticated(false);
        }
      } else {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials) => {
    try {
      const response = await ApiService.login(credentials);
      const { access_token, user: userData } = response;
      
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      setUser(userData);
      setIsAuthenticated(true);
      localStorage.setItem('preferred_language', userData.preferred_language || 'en');
      i18n.changeLanguage(userData.preferred_language || 'en');
      
      return { success: true, user: userData };
    } catch (error) {
      return { 
        success: false, 
        error: errorMessage(error, 'Login failed') 
      };
    }
  };

  const signup = async (userData) => {
    try {
      const response = await ApiService.signup(userData);
      const { access_token, user: newUser } = response;
      
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(newUser));
      
      setUser(newUser);
      setIsAuthenticated(true);
      localStorage.setItem('preferred_language', newUser.preferred_language || 'en');
      i18n.changeLanguage(newUser.preferred_language || 'en');
      
      return { success: true, user: newUser };
    } catch (error) {
      return { 
        success: false, 
        error: errorMessage(error, 'Signup failed') 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

  const updateUser = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const updateLanguage = async (preferredLanguage) => {
    const userData = await ApiService.updatePreferredLanguage(preferredLanguage);
    updateUser(userData);
    localStorage.setItem('preferred_language', preferredLanguage);
    i18n.changeLanguage(preferredLanguage);
    return userData;
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    signup,
    logout,
    updateUser,
    updateLanguage
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
