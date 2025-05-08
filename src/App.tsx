import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AssetProvider } from './contexts/AssetContext';
import { OperationsProvider } from './contexts/OperationsContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { UserOperationsHistoryProvider } from './contexts/UserOperationsHistoryContext';
import PrivateRoute from './components/PrivateRoute';

// Pages
import Welcome from './pages/Welcome';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import AdminDebug from './pages/AdminDebug';

function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <AssetProvider>
          <OperationsProvider>
            <UserOperationsHistoryProvider>
              <Router>
                <Routes>
                  <Route path="/" element={<Welcome />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  
                  {/* Novas rotas protegidas como filhas do elemento PrivateRoute */}
                  <Route element={<PrivateRoute />}> 
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/admin/debug" element={<AdminDebug />} />
                  </Route>
                  
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Router>
            </UserOperationsHistoryProvider>
          </OperationsProvider>
        </AssetProvider>
      </NotificationProvider>
    </AuthProvider>
  );
}

export default App;