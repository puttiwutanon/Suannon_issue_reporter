import React, { useEffect, useState } from 'react';
import liff from '@line/liff';
import IssueFormASAP from './components/IssueFormASAP';
import IssueFormLongTerm from './components/IssueFormLongTerm';
import IssueCheck from './components/IssueCheck';

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('form_urgent');

  useEffect(() => {
    // Read mode from URL
    const params = new URLSearchParams(window.location.search);
    const modeParam = params.get('mode');
    if (modeParam) setMode(modeParam);

    // Initialize LIFF
    liff.init({ liffId: import.meta.env.VITE_LIFF_ID })
      .then(async () => {
        // If mode === 'home', close the window and return
        if (modeParam === 'home') {
          if (liff.isInClient()) {
            liff.closeWindow();
          }
          return; // don't go further
        }

        // Otherwise, proceed with login and profile fetch
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

  // If mode is home, we never reach this point because we close the window
  // But add a fallback just in case
  if (mode === 'home') {
    return null; // or a small "กำลังปิด..." message
  }

  if (error) return <div style={{ padding: 20, color: 'red' }}>Error: {error}</div>;
  if (!profile) return <div style={{ padding: 20 }}>Loading LINE profile...</div>;

  let Component;
  let props = { profile };

  if (mode === 'form_urgent') {
    Component = IssueFormASAP;
  } else if (mode === 'form_suggestion') {
    Component = IssueFormLongTerm;
  } else if (mode === 'view_mine' || mode === 'view_others') {
    Component = IssueCheck;
    props = { profile, viewMode: mode };
  } else {
    Component = IssueFormASAP; // fallback
  }

  return <Component {...props} />;
}