import React, { useState, useEffect } from 'react';
import liff from '@line/liff';
import './styles/IssueCheckStyle.scss';

// ---------- Logger (writes to console with timestamps) ----------
const logger = {
  info: (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
    if (data) {
      console.log(`[${timestamp}] ℹ️ ${message}`, data);
    } else {
      console.log(`[${timestamp}] ℹ️ ${message}`);
    }
  },
  error: (message, error = null) => {
    const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
    if (error) {
      console.error(`[${timestamp}] ❌ ${message}`, error);
    } else {
      console.error(`[${timestamp}] ❌ ${message}`);
    }
  },
  debug: (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
    if (data) {
      console.debug(`[${timestamp}] 🔍 ${message}`, data);
    } else {
      console.debug(`[${timestamp}] 🔍 ${message}`);
    }
  },
  success: (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
    if (data) {
      console.log(`[${timestamp}] ✅ ${message}`, data);
    } else {
      console.log(`[${timestamp}] ✅ ${message}`);
    }
  },
};

export default function IssueCheck({ profile, viewMode }) {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchIssues = async () => {
      const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
      logger.info(`🚀 Fetching issues started - ViewMode: ${viewMode}`);
      logger.debug(`👤 Profile:`, { userId: profile.userId, displayName: profile.displayName });

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        logger.debug(`📡 API URL from env: ${apiUrl}`);
        
        let url = `${apiUrl}/api/issues`;
        logger.debug(`🔗 Base URL: ${url}`);
        
        if (viewMode === 'view_mine') {
          url += `?user_id=${profile.userId}`;
          logger.info(`🔍 Filtering by user_id: ${profile.userId}`);
        }
        
        logger.info(`🔗 Final fetch URL: ${url}`);

        const startTime = Date.now();
        logger.info(`⏳ Sending request...`);

        const res = await fetch(url, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        const elapsed = Date.now() - startTime;
        logger.info(`⏱️ Request completed in ${elapsed}ms`);
        logger.info(`📡 Response status: ${res.status} ${res.statusText}`);

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();
        logger.success(`📦 API response received`, {
          success: data.success,
          issuesCount: data.issues?.length || 0
        });

        if (data.success) {
          let fetched = data.issues;
          if (viewMode === 'view_others') {
            logger.info(`🔍 Filtering for 'others' mode - excluding user ${profile.userId}`);
            const beforeCount = fetched.length;
            fetched = fetched.filter(issue => issue.lineUserId !== profile.userId);
            logger.info(`📊 Filtered from ${beforeCount} to ${fetched.length} issues`);
          }
          setIssues(fetched);
          logger.success(`✅ Set ${fetched.length} issues in state`);
        } else {
          logger.error(`❌ API returned success: false`);
          setError('API returned success: false');
          setIssues([]);
        }
      } catch (err) {
        logger.error(`❌ Fetch error: ${err.message}`, {
          name: err.name,
          stack: err.stack
        });
        setError(`Failed to fetch: ${err.message}`);
        setIssues([]);
      } finally {
        setLoading(false);
        logger.info(`🏁 Fetch completed - Loading: ${loading}`);
      }
    };

    fetchIssues();
  }, [profile, viewMode]);

  // ... (rest of the component remains the same)
  
  if (loading) {
    return (
      <div className="container">
        <div className="header">
          <h2 className="title">
            {viewMode === 'view_mine' ? '📋 เรื่องแจ้งของฉัน' : '📋 เรื่องแจ้งจากผู้อื่น'}
          </h2>
          <span className="count">กำลังโหลด...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="header">
          <h2 className="title">
            {viewMode === 'view_mine' ? '📋 เรื่องแจ้งของฉัน' : '📋 เรื่องแจ้งจากผู้อื่น'}
          </h2>
          <span className="count">เกิดข้อผิดพลาด</span>
        </div>
        <div className="empty" style={{ color: 'red' }}>Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <h2 className="title">
          {viewMode === 'view_mine' ? '📋 เรื่องแจ้งของฉัน' : '📋 เรื่องแจ้งจากผู้อื่น'}
        </h2>
        <span className="count">{issues.length} เรื่อง</span>
      </div>

      {issues.length === 0 ? (
        <div className="empty">ยังไม่มีเรื่องแจ้งในหมวดนี้</div>
      ) : (
        <>
          {/* ---------- Card View ---------- */}
          {issues.map((issue) => (
            <div key={issue.id} className="card">
              <div className="card-header">
                <span className="category">#{issue.category}</span>
                <span className="status">
                  {issue.status === 'pending' ? '⏳ รอดำเนินการ' : '✅ เสร็จสิ้น'}
                </span>
              </div>
              <div className="card-body">
                {issue.imageUrl && (
                  <img src={issue.imageUrl} alt="issue" className="thumb" />
                )}
                <div className="card-content">
                  <p className="desc">{issue.description}</p>
                  <p className="meta">
                    {issue.reporterName} · {new Date(issue.createdAt).toLocaleDateString('th-TH')}
                  </p>
                  {issue.studentYear && (
                    <p className="meta">
                      ชั้น {issue.studentYear}/{issue.studentClass} เลขที่ {issue.studentNumber}
                    </p>
                  )}
                  {issue.latitude && (
                    <p className="meta">📍 {issue.latitude.toFixed(5)}, {issue.longitude.toFixed(5)}</p>
                  )}
                </div>
              </div>
            </div>
          ))}

        </>
      )}
    </div>
  );
}

// Table styles
const tableHeader = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 'bold',
  color: '#374151',
  fontSize: 13,
};
const tableCell = {
  padding: '8px 12px',
  borderBottom: '1px solid #E5E7EB',
  color: '#4B5563',
  fontSize: 13,
};