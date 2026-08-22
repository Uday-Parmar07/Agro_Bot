import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Dashboard from './components/Dashboard';
import Home from './pages/Home';
import Analytics from './pages/Analytics';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Questionnaire from './pages/Questionnaire';
import DiseaseCheckup from './pages/DiseaseCheckup';
import GovernmentSchemes from './pages/GovernmentSchemes';
import AdvisorDashboard from './pages/AdvisorDashboard';
import Finance from './pages/Finance';
import Marketplace from './pages/Marketplace';
import Community from './pages/Community';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }
  
  return !isAuthenticated ? children : <Navigate to="/dashboard" />;
};

const RoleRoute = ({ roles, children }) => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" />;
  return roles.includes(user?.role) ? children : <Navigate to="/dashboard" />;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      <Route path="/signup" element={
        <PublicRoute>
          <Signup />
        </PublicRoute>
      } />
      
      {/* Protected Routes */}
      <Route path="/questionnaire" element={
        <ProtectedRoute>
          <Questionnaire />
        </ProtectedRoute>
      } />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
      <Route path="/analytics" element={
        <ProtectedRoute>
          <Analytics />
        </ProtectedRoute>
      } />
      <Route path="/disease-checkup" element={
        <ProtectedRoute>
          <DiseaseCheckup />
        </ProtectedRoute>
      } />
      <Route path="/government-schemes" element={
        <ProtectedRoute>
          <GovernmentSchemes />
        </ProtectedRoute>
      } />
      <Route path="/finance" element={
        <ProtectedRoute>
          <Finance />
        </ProtectedRoute>
      } />
      <Route path="/marketplace" element={
        <ProtectedRoute>
          <Marketplace />
        </ProtectedRoute>
      } />
      <Route path="/community" element={
        <ProtectedRoute>
          <Community />
        </ProtectedRoute>
      } />
      <Route path="/advisor" element={
        <RoleRoute roles={['advisor', 'admin']}>
          <AdvisorDashboard />
        </RoleRoute>
      } />
      
      {/* Catch all route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </div>
  );
}

export default App;
