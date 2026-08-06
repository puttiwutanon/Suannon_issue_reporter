import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { doSignOut } from '../firebase/auth';
import './styles/IssueDashboardStyle.scss';

function IssuePDFReportPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const navigate = useNavigate();

  const fetchReports = async () => {
    try {
      setLoading(true);
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/reports-list?ngrok-skip-browser-warning=true`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch reports');
      const data = await res.json();
      if (data.success) {
        setReports(data.reports);
      } else {
        setError('ไม่สามารถโหลดรายการรายงานได้');
      }
    } catch (err) {
      console.error('Fetch reports error:', err);
      setError('เกิดข้อผิดพลาดในการโหลดข้อมูล');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleGenerateReport = async () => {
    setGenerating(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/generate-report?ngrok-skip-browser-warning=true`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to generate report');
      const data = await res.json();
      if (data.success) {
        alert('✅ สร้างรายงานสำเร็จ!');
        await fetchReports(); // Refresh the list
      } else {
        alert(`⚠️ ${data.message || 'ไม่สามารถสร้างรายงานได้'}`);
      }
    } catch (err) {
      console.error('Generate report error:', err);
      alert('❌ เกิดข้อผิดพลาดในการสร้างรายงาน');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadReport = (filename) => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const url = `${apiUrl}/api/download-report/${filename}?ngrok-skip-browser-warning=true`;
    window.open(url, '_blank');
  };

  const handleLogout = async () => {
    if (window.confirm('คุณต้องการออกจากระบบใช่หรือไม่?')) {
      try {
        await doSignOut();
        sessionStorage.removeItem('admin_logged_in');
        navigate('/admin/login');
      } catch (err) {
        console.error('Logout error:', err);
      }
    }
  };

  const handleBack = () => {
    navigate('/admin/dashboard');
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return 'ไม่ระบุ';
    try {
      const parts = dateStr.split('/');
      if (parts.length === 3) {
        return `${parts[0]}/${parts[1]}/${parts[2]}`;
      }
      return dateStr;
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">กำลังโหลดรายการรายงาน...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <h1>📄 รายงาน PDF</h1>
        <div className="header-actions">
          <button onClick={handleBack} className="back-btn">
            ⬅️ กลับ
          </button>
          <button onClick={handleLogout} className="logout-btn">
            🚪 ออกจากระบบ
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="report-actions">
        <button 
          className="generate-report-btn" 
          onClick={handleGenerateReport}
          disabled={generating}
        >
          {generating ? '⏳ กำลังสร้าง...' : '📝 สร้างรายงานวันนี้'}
        </button>
        <span className="report-hint">
          ระบบจะสร้างรายงานอัตโนมัติทุกวันเวลา 18:00 น.
        </span>
      </div>

      {/* Reports List */}
      <div className="reports-list-container">
        <h2>📋 รายการรายงานทั้งหมด</h2>
        {error ? (
          <div className="error-state">{error}</div>
        ) : reports.length === 0 ? (
          <div className="empty-state">
            <p>ยังไม่มีรายงาน</p>
            <p style={{ fontSize: '14px', color: '#6B7280' }}>
              กดปุ่ม "สร้างรายงานวันนี้" เพื่อสร้างรายงานแรก
            </p>
          </div>
        ) : (
          <div className="reports-table-wrapper">
            <table className="reports-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>วันที่</th>
                  <th>เวลาที่สร้าง</th>
                  <th>ชื่อไฟล์</th>
                  <th>ดาวน์โหลด</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report, index) => (
                  <tr key={report.filename}>
                    <td>{index + 1}</td>
                    <td>{formatDate(report.date)}</td>
                    <td>{report.time ? `${report.time.slice(0, 2)}:${report.time.slice(2, 4)}` : '-'}</td>
                    <td className="filename-cell">{report.filename}</td>
                    <td>
                      <button 
                        className="download-btn"
                        onClick={() => handleDownloadReport(report.filename)}
                      >
                        ⬇️ ดาวน์โหลด
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="report-footer">
        <p>
          💡 รายงานจะแสดงเฉพาะปัญหาเร่งด่วน (🚨) ที่ยังรอดำเนินการในแต่ละวัน
        </p>
        <p>
          📌 ไฟล์ PDF จะถูกเก็บไว้ในเซิร์ฟเวอร์และสามารถดาวน์โหลดได้ทุกเมื่อ
        </p>
      </div>
    </div>
  );
}

export default IssuePDFReportPage;