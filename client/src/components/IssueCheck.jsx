import React, { useState, useEffect } from 'react';
import liff from '@line/liff';
import './styles/IssueCheckStyle.scss';

export default function IssueCheck({ profile, viewMode }) {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchIssues = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        let url = `${apiUrl}/api/issues`;
        if (viewMode === 'view_mine') {
          url += `?user_id=${profile.userId}`;
        }

        const res = await fetch(url);
        if (!res.ok) throw new Error('API error');

        const data = await res.json();
        if (data.success) {
          let fetched = data.issues;
          if (viewMode === 'view_others') {
            fetched = fetched.filter(issue => issue.lineUserId !== profile.userId);
          }
          setIssues(fetched);
        } else {
          setIssues([]);
        }
      } catch (err) {
        console.warn('Could not fetch issues, showing empty list.');
        setIssues([]);
      } finally {
        setLoading(false);
      }
    };

    fetchIssues();
  }, [profile, viewMode]);

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
        issues.map((issue) => (
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
        ))
      )}
    </div>
  );
}