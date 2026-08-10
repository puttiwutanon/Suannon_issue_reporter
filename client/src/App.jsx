import React, { useEffect, useState } from 'react';
import liff from '@line/liff';
import IssueFormASAP from './components/IssueFormASAP';
import IssueFormLongTerm from './components/IssueFormLongTerm';
import IssueCheck from './components/IssueCheck';

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('form_urgent');
  const [idToken, setIdToken] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const modeParam = params.get('mode');
    if (modeParam) setMode(modeParam);

    liff.init({ liffId: import.meta.env.VITE_LIFF_ID })
      .then(async () => {
        if (modeParam === 'home') {
          if (liff.isInClient()) {
            liff.closeWindow();
          }
          return;
        }

        if (!liff.isLoggedIn()) {
          liff.login();
        } else {
          const userProfile = await liff.getProfile();
          const token = liff.getIDToken();
          setProfile(userProfile);
          setIdToken(token);
        }
      })
      .catch((err) => {
        console.error('LIFF Init Error:', err);
        setError(err.toString());
      });
  }, []);

  if (mode === 'home') {
    return null;
  }

  if (error) return <div style={{ padding: 20, color: 'red' }}>Error: {error}</div>;
  if (!profile) return <div style={{ padding: 20 }}>Loading LINE profile...</div>;

  let Component;
  let props = { profile, idToken };

  if (mode === 'form_urgent') {
    Component = IssueFormASAP;
  } else if (mode === 'form_suggestion') {
    Component = IssueFormLongTerm;
  } else if (mode === 'view_mine' || mode === 'view_others') {
    Component = IssueCheck;
    props = { profile, idToken, viewMode: mode };
  } else {
    Component = IssueFormASAP;
  }

  return <Component {...props} />;
}