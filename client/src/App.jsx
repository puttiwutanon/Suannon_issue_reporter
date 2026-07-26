import React, { useEffect, useState } from 'react';
import liff from '@line/liff';
import IssueForm from './components/IssueFormASAP';

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Initialize LIFF
    liff.init({ liffId: import.meta.env.VITE_LIFF_ID })
      .then(async () => {
        if (!liff.isLoggedIn()) {
          liff.login();
        } else {
          const userProfile = await liff.getProfile();
          setProfile(userProfile);
        }
      })
      .catch((err) => {
        console.error('LIFF Init Error:', err);
        setError(err.toString());
      });
  }, []);

  if (error) {
    return <div style={{ padding: 20, color: 'red' }}>Error initializing LIFF: {error}</div>;
  }

  if (!profile) {
    return <div style={{ padding: 20 }}>Loading LINE profile...</div>;
  }

  // Pass the loaded profile data down into your form component
  return <IssueForm profile={profile} />;
}