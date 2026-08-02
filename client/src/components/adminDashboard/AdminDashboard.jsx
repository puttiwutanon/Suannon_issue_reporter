import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { onAuthStateChange } from '../../firebase/auth.js';
import IssueDashboard from '../../components/IssueDashboard';
import '../styles/IssueDashboardStyle.scss';

function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onAuthStateChange((user) => {
      if (user) {
        setUser(user);
        setLoading(false);
      } else {
        // Redirect to login if not authenticated
        navigate('/admin/login');
      }
    });

    // Cleanup subscription
    return () => unsubscribe();
  }, [navigate]);

  if (loading) {
    return (
      <div className="dashboard-wrapper">
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>กำลังโหลด...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null; // Will redirect
  }

  return <IssueDashboard />;
}

export default AdminDashboard;