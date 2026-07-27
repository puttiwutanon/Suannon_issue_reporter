import React, { useState, useEffect } from 'react';
import liff from '@line/liff';

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
          // If API returns success: false, treat as empty
          setIssues([]);
        }
      } catch (err) {
        // Silently handle error – just show empty state
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
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>
            {viewMode === 'view_mine' ? '📋 เรื่องแจ้งของฉัน' : '📋 เรื่องแจ้งจากผู้อื่น'}
          </h2>
          <span style={styles.count}>กำลังโหลด...</span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>
          {viewMode === 'view_mine' ? '📋 เรื่องแจ้งของฉัน' : '📋 เรื่องแจ้งจากผู้อื่น'}
        </h2>
        <span style={styles.count}>{issues.length} เรื่อง</span>
      </div>

      {issues.length === 0 ? (
        // Empty state – only show a minimal message, no extra cards
        <div style={styles.empty}>ยังไม่มีเรื่องแจ้งในหมวดนี้</div>
      ) : (
        issues.map((issue) => (
          <div key={issue.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.category}>#{issue.category}</span>
              <span style={styles.status}>
                {issue.status === 'pending' ? '⏳ รอดำเนินการ' : '✅ เสร็จสิ้น'}
              </span>
            </div>
            <div style={styles.cardBody}>
              {issue.imageUrl && (
                <img src={issue.imageUrl} alt="issue" style={styles.thumb} />
              )}
              <div style={styles.cardContent}>
                <p style={styles.desc}>{issue.description}</p>
                <p style={styles.meta}>
                  {issue.reporterName} · {new Date(issue.createdAt).toLocaleDateString('th-TH')}
                </p>
                {issue.studentYear && (
                  <p style={styles.meta}>
                    ชั้น {issue.studentYear}/{issue.studentClass} เลขที่ {issue.studentNumber}
                  </p>
                )}
                {issue.latitude && (
                  <p style={styles.meta}>📍 {issue.latitude.toFixed(5)}, {issue.longitude.toFixed(5)}</p>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ---------- Styles ----------
const styles = {
  container: { backgroundColor: '#F3F4F6', minHeight: '100vh', padding: '16px', fontFamily: 'sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' },
  title: { fontSize: '20px', fontWeight: 'bold', color: '#111827', margin: 0 },
  count: { fontSize: '14px', color: '#6B7280' },
  empty: { textAlign: 'center', padding: '40px', color: '#6B7280', fontSize: '16px' },
  card: { backgroundColor: '#FFF', borderRadius: '12px', padding: '16px', marginBottom: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
  category: { fontSize: '13px', backgroundColor: '#E5E7EB', padding: '2px 10px', borderRadius: '20px', color: '#374151' },
  status: { fontSize: '13px', fontWeight: 'bold', color: '#4B5563' },
  cardBody: { display: 'flex', gap: '12px' },
  thumb: { width: '80px', height: '80px', objectFit: 'cover', borderRadius: '8px', flexShrink: 0 },
  cardContent: { flex: 1 },
  desc: { margin: '0 0 6px 0', fontSize: '15px', color: '#1F2937' },
  meta: { margin: '2px 0', fontSize: '13px', color: '#6B7280' },
};