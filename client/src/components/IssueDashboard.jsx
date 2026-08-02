import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import liff from '@line/liff';
import './styles/IssueDashboardStyle.scss';
import { doSignOut } from '../firebase/auth';
import { useNavigate } from 'react-router-dom';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons for different issue types
const getMarkerIcon = (issueType, category) => {
  const color = issueType === 'suggestion' ? '#4CAF50' : '#f44336';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="background-color: ${color}; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 16px; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
      ${issueType === 'suggestion' ? '💡' : '🚨'}
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
};

// Component to fit map to markers
function FitBounds({ markers }) {
  const map = useMap();
  
  useEffect(() => {
    if (markers.length > 0) {
      const bounds = L.latLngBounds(markers.map(m => [m.latitude, m.longitude]));
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [markers, map]);
  
  return null;
}

// Component to change map view
function ChangeView({ center, zoom }) {
  const map = useMap();
  map.setView(center, zoom);
  return null;
}

function IssueDashboard() {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'urgent', 'suggestion'
  const [searchTerm, setSearchTerm] = useState('');
  const [mapCenter] = useState([13.7563, 100.5018]); // Default: Bangkok
  const [mapZoom] = useState(12);
  const navigate = useNavigate();

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

  useEffect(() => {
    fetchIssues();
  }, []);

const fetchIssues = async () => {
  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const url = `${apiUrl}/api/issues`;

    const res = await fetch(url, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
      },
    });
    if (!res.ok) throw new Error('API error: ' + res.status);

    const data = await res.json();
    if (data.success) {
      setIssues(data.issues);
    } else {
      setError('Failed to fetch issues');
    }
  } catch (err) {
    console.error('Fetch error:', err);
    setError(err.message);
  } finally {
    setLoading(false);
  }
};

  // Filter issues
  const filteredIssues = issues.filter(issue => {
    // Type filter
    if (filter === 'urgent' && issue.issueType !== 'urgent') return false;
    if (filter === 'suggestion' && issue.issueType !== 'suggestion') return false;
    
    // Search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        issue.description?.toLowerCase().includes(search) ||
        issue.reporterName?.toLowerCase().includes(search) ||
        issue.category?.toLowerCase().includes(search)
      );
    }
    
    return true;
  });

  // Separate issues with location for map
  const locatedIssues = filteredIssues.filter(issue => issue.latitude && issue.longitude);

  // Stats
  const totalIssues = issues.length;
  const urgentCount = issues.filter(i => i.issueType === 'urgent').length;
  const suggestionCount = issues.filter(i => i.issueType === 'suggestion').length;
  const pendingCount = issues.filter(i => i.status === 'pending').length;
  const resolvedCount = issues.filter(i => i.status === 'resolved').length;

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">กำลังโหลดข้อมูล...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="error-state">Error: {error}</div>
      </div>
    );
  }

  return (
    <>
        <div className="dashboard-container">   
        {/* Header */}
        <div className="dashboard-header">
        <h1>📊 แผงควบคุมปัญหา</h1>
        <div className="header-actions">
            <button onClick={handleLogout} className="logout-btn">
            🚪 ออกจากระบบ
            </button>
            <button onClick={() => window.location.reload()} className="refresh-btn">
            🔄 รีเฟรช
            </button>
        </div>
        </div>

        {/* Stats Cards */}
        <div className="stats-grid">
            <div className="stat-card total">
            <div className="stat-number">{totalIssues}</div>
            <div className="stat-label">เรื่องทั้งหมด</div>
            </div>
            <div className="stat-card urgent">
            <div className="stat-number">{urgentCount}</div>
            <div className="stat-label">🚨 ด่วน</div>
            </div>
            <div className="stat-card suggestion">
            <div className="stat-number">{suggestionCount}</div>
            <div className="stat-label">💡 ข้อเสนอแนะ</div>
            </div>
            <div className="stat-card pending">
            <div className="stat-number">{pendingCount}</div>
            <div className="stat-label">⏳ รอดำเนินการ</div>
            </div>
            <div className="stat-card resolved">
            <div className="stat-number">{resolvedCount}</div>
            <div className="stat-label">✅ เสร็จสิ้น</div>
            </div>
        </div>

        {/* Filters & Search */}
        <div className="controls">
            <div className="filter-buttons">
            <button 
                className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
            >
                ทั้งหมด
            </button>
            <button 
                className={`filter-btn urgent ${filter === 'urgent' ? 'active' : ''}`}
                onClick={() => setFilter('urgent')}
            >
                🚨 ด่วน
            </button>
            <button 
                className={`filter-btn suggestion ${filter === 'suggestion' ? 'active' : ''}`}
                onClick={() => setFilter('suggestion')}
            >
                💡 ข้อเสนอแนะ
            </button>
            </div>
            <div className="search-box">
            <input
                type="text"
                placeholder="🔍 ค้นหา..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
            />
            </div>
        </div>

        {/* Map */}
        <div className="map-container">
            {locatedIssues.length > 0 ? (
            <MapContainer
                center={mapCenter}
                zoom={mapZoom}
                style={{ height: '100%', width: '100%', borderRadius: '8px' }}
            >
                <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                {locatedIssues.map((issue) => (
                <Marker
                    key={issue.id}
                    position={[issue.latitude, issue.longitude]}
                    icon={getMarkerIcon(issue.issueType, issue.category)}
                    eventHandlers={{
                    click: () => setSelectedIssue(issue),
                    }}
                >
                    <Popup>
                    <div className="popup-content">
                        <h4>{issue.category}</h4>
                        <p>{issue.description?.substring(0, 100)}...</p>
                        <small>ผู้แจ้ง: {issue.reporterName}</small><br />
                        <small>{new Date(issue.createdAt).toLocaleString('th-TH')}</small>
                        <br />
                        <span className={`status-badge ${issue.status}`}>
                        {issue.status === 'pending' ? '⏳ รอดำเนินการ' : '✅ เสร็จสิ้น'}
                        </span>
                    </div>
                    </Popup>
                </Marker>
                ))}
                <FitBounds markers={locatedIssues} />
            </MapContainer>
            ) : (
            <div className="no-location-message">
                <p>📍 ไม่มีรายการที่มีตำแหน่งที่ตั้ง</p>
            </div>
            )}
        </div>

        {/* Issues List */}
        <div className="issues-list">
            <h2>📋 รายการแจ้งทั้งหมด ({filteredIssues.length})</h2>
            {filteredIssues.length === 0 ? (
            <div className="empty-state">ไม่มีรายการที่ตรงกับเงื่อนไข</div>
            ) : (
            filteredIssues.map((issue) => (
                <div 
                key={issue.id} 
                className={`issue-card ${issue.issueType === 'suggestion' ? 'suggestion' : 'urgent'}`}
                onClick={() => setSelectedIssue(issue)}
                >
                <div className="issue-header">
                    <div className="issue-badge">
                    {issue.issueType === 'suggestion' ? '💡' : '🚨'}
                    <span className={`type-badge ${issue.issueType}`}>
                        {issue.issueType === 'suggestion' ? 'ข้อเสนอแนะ' : 'แจ้งด่วน'}
                    </span>
                    </div>
                    <div className="issue-meta">
                    <span className="category-badge">{issue.category}</span>
                    <span className={`status-badge ${issue.status}`}>
                        {issue.status === 'pending' ? '⏳ รอดำเนินการ' : '✅ เสร็จสิ้น'}
                    </span>
                    </div>
                </div>
                
                <div className="issue-body">
                    <p className="issue-description">{issue.description}</p>
                    {issue.imageUrl && (
                    <img src={issue.imageUrl} alt="Issue" className="issue-thumbnail" />
                    )}
                </div>
                
                <div className="issue-footer">
                    <span className="reporter">👤 {issue.reporterName}</span>
                    {issue.studentYear && (
                    <span className="student-info">
                        ชั้น {issue.studentYear}/{issue.studentClass} เลขที่ {issue.studentNumber}
                    </span>
                    )}
                    <span className="date">
                    {new Date(issue.createdAt).toLocaleString('th-TH')}
                    </span>
                    {issue.latitude && (
                    <span className="location">📍 มีตำแหน่งที่ตั้ง</span>
                    )}
                </div>
                </div>
            ))
            )}
        </div>

        {/* Selected Issue Modal */}
        {selectedIssue && (
            <div className="modal-overlay" onClick={() => setSelectedIssue(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close" onClick={() => setSelectedIssue(null)}>✕</button>
                <h3>{selectedIssue.category}</h3>
                <p><strong>ประเภท:</strong> {selectedIssue.issueType === 'suggestion' ? 'ข้อเสนอแนะ' : 'แจ้งด่วน'}</p>
                <p><strong>รายละเอียด:</strong> {selectedIssue.description}</p>
                <p><strong>ผู้แจ้ง:</strong> {selectedIssue.reporterName}</p>
                {selectedIssue.studentYear && (
                <p><strong>นักเรียน:</strong> ชั้น {selectedIssue.studentYear}/{selectedIssue.studentClass} เลขที่ {selectedIssue.studentNumber}</p>
                )}
                <p><strong>สถานะ:</strong> {selectedIssue.status === 'pending' ? '⏳ รอดำเนินการ' : '✅ เสร็จสิ้น'}</p>
                <p><strong>วันที่:</strong> {new Date(selectedIssue.createdAt).toLocaleString('th-TH')}</p>
                {selectedIssue.latitude && (
                <p><strong>📍 ตำแหน่ง:</strong> {selectedIssue.latitude}, {selectedIssue.longitude}</p>
                )}
                {selectedIssue.imageUrl && (
                <img src={selectedIssue.imageUrl} alt="Issue" className="modal-image" />
                )}
            </div>
            </div>
        )}
        </div>
    </>
  )
}

export default IssueDashboard