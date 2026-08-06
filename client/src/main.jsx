import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import App from './App.jsx';
import AdminLogin from './components/adminDashboard/AdminLogin.jsx';
import AdminDashboard from './components/adminDashboard/AdminDashboard.jsx';
import IssuePDFReportPage from './components/IssuePDFReportPage.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Main LIFF App - accessible from LINE */}
        <Route path="/" element={<App />} />
        
        {/* Admin Routes */}
        <Route path="/admin" element={<Navigate to="/admin/login" replace />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/admin/reports" element={<IssuePDFReportPage />} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/admin/login" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);