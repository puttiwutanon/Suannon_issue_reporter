import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './styles/IssueDashboardStyle.scss';
import { doSignOut } from '../firebase/auth';
import { useNavigate } from 'react-router-dom';

// School coordinates (13°54'48.6"N 100°30'18.7"E)
const SCHOOL_COORDS = {
  lat: 13.910305,
  lng: 100.512396,
};

// School bounds - slightly larger to allow some movement
const SCHOOL_BOUNDS = {
  north: 13.9130,
  south: 13.9076,
  east: 100.5156,
  west: 100.5092,
};

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Component to handle map restrictions and centering
function MapRestrictions({ bounds, center, zoom, markers }) {
  const map = useMap();

  useEffect(() => {
    if (map) {
      map.setView(center, zoom, { animate: true, duration: 0.5 });
    }
  }, [map, center, zoom]);

  useEffect(() => {
    if (map && bounds) {
      map.setMaxBounds([
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      ]);
    }
    
    return () => {
      if (map) {
        map.setMaxBounds(null);
      }
    };
  }, [map, bounds]);

  useMapEvents({
    drag: () => {
      const currentBounds = map.getBounds();
      if (currentBounds.getSouth() < SCHOOL_BOUNDS.south || 
          currentBounds.getNorth() > SCHOOL_BOUNDS.north ||
          currentBounds.getWest() < SCHOOL_BOUNDS.west ||
          currentBounds.getEast() > SCHOOL_BOUNDS.east) {
        map.panTo(SCHOOL_COORDS, { animate: true, duration: 0.3 });
      }
    },
    zoomend: () => {
      if (map.getZoom() < 15) {
        map.setZoom(15, { animate: true });
      }
    },
  });

  return null;
}

// Custom marker icons for different issue types
const getMarkerIcon = (issueType) => {
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

// Memoized Marker component
const MemoizedMarker = React.memo(({ issue, setSelectedIssue }) => {
  const icon = useMemo(() => getMarkerIcon(issue.issueType), [issue.issueType]);
  
  return (
    <Marker
      position={[issue.latitude, issue.longitude]}
      icon={icon}
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
  );
});

function IssueDashboard() {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [mapKey, setMapKey] = useState(Date.now());
  const navigate = useNavigate();
  const [showFixModal, setShowFixModal] = useState(false);
  const [selectedIssueId, setSelectedIssueId] = useState(null);
  const [fixFile, setFixFile] = useState(null);
  const [fixPreview, setFixPreview] = useState(null);
  const [fixing, setFixing] = useState(false);

  const handleLogout = useCallback(async () => {
    if (window.confirm('คุณต้องการออกจากระบบใช่หรือไม่?')) {
      try {
        await doSignOut();
        sessionStorage.removeItem('admin_logged_in');
        navigate('/admin/login');
      } catch (err) {
        console.error('Logout error:', err);
      }
    }
  }, [navigate]);

  // Navigate to PDF Reports Page
  const handleGoToReports = () => {
    navigate('/admin/reports');
  };

  const handleFixImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFixFile(file);
      setFixPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmitFix = async () => {
    if (!fixFile) {
      alert('กรุณาเลือกรูปภาพ');
      return;
    }
    setFixing(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const formData = new FormData();
      formData.append('fix_image', fixFile);

      const res = await fetch(`${apiUrl}/api/issues?ngrok-skip-browser-warning=true`, {
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      });
      if (!res.ok) throw new Error('Failed to resolve issue');
      const data = await res.json();
      if (data.success) {
        alert('✅ แจ้งว่าซ่อมแล้วสำเร็จ!');
        setShowFixModal(false);
        setFixFile(null);
        setFixPreview(null);
        setSelectedIssueId(null);
        fetchIssues();
      } else {
        alert('❌ เกิดข้อผิดพลาด');
      }
    } catch (err) {
      console.error(err);
      alert('❌ ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์');
    } finally {
      setFixing(false);
    }
  };

  const fetchIssues = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  const filteredIssues = useMemo(() => {
    return issues.filter(issue => {
      if (filter === 'urgent' && issue.issueType !== 'urgent') return false;
      if (filter === 'suggestion' && issue.issueType !== 'suggestion') return false;
      
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
  }, [issues, filter, searchTerm]);

  const locatedIssues = useMemo(() => {
    return filteredIssues.filter(issue => issue.latitude && issue.longitude);
  }, [filteredIssues]);

  const stats = useMemo(() => {
    return {
      total: issues.length,
      urgent: issues.filter(i => i.issueType === 'urgent').length,
      suggestion: issues.filter(i => i.issueType === 'suggestion').length,
      pending: issues.filter(i => i.status === 'pending').length,
      resolved: issues.filter(i => i.status === 'resolved').length,
    };
  }, [issues]);

  useEffect(() => {
    if (!loading && issues.length > 0) {
      setMapKey(Date.now());
    }
  }, [loading, issues]);

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
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">เรื่องทั้งหมด</div>
        </div>
        <div className="stat-card urgent">
          <div className="stat-number">{stats.urgent}</div>
          <div className="stat-label">🚨 ด่วน</div>
        </div>
        <div className="stat-card suggestion">
          <div className="stat-number">{stats.suggestion}</div>
          <div className="stat-label">💡 ข้อเสนอแนะ</div>
        </div>
        <div className="stat-card pending">
          <div className="stat-number">{stats.pending}</div>
          <div className="stat-label">⏳ รอดำเนินการ</div>
        </div>
        <div className="stat-card resolved">
          <div className="stat-number">{stats.resolved}</div>
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

      {/* Map Container */}
      <div className="map-container">
        {locatedIssues.length > 0 ? (
          <MapContainer
            key={mapKey}
            center={SCHOOL_COORDS}
            zoom={17}
            style={{ height: '100%', width: '100%', borderRadius: '8px' }}
            zoomControl={true}
            scrollWheelZoom={true}
            dragging={true}
            easeLinearity={0.35}
            fadeAnimation={true}
            markerZoomAnimation={true}
            zoomAnimation={true}
            maxZoom={20}
            minZoom={15}
            zoomSnap={0.5}
            zoomDelta={0.5}
          >
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='&copy; <a href="https://www.esri.com">Esri</a>'
              maxZoom={19}
            />
            
            <MapRestrictions 
              bounds={SCHOOL_BOUNDS}
              center={SCHOOL_COORDS}
              zoom={17}
              markers={locatedIssues}
            />
            
            <Marker
              position={[SCHOOL_COORDS.lat, SCHOOL_COORDS.lng]}
              icon={L.divIcon({
                className: 'school-marker',
                html: `<div style="background-color: #3B82F6; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">🏫</div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10],
              })}
            >
              <Popup>
                <div className="popup-content">
                  <h4>🏫 โรงเรียน</h4>
                  <p>ที่ตั้งของโรงเรียน</p>
                </div>
              </Popup>
            </Marker>
            
            {locatedIssues.map((issue) => (
              <MemoizedMarker 
                key={issue.id} 
                issue={issue} 
                setSelectedIssue={setSelectedIssue} 
              />
            ))}
          </MapContainer>
        ) : (
          <div className="no-location-message">
            <p>📍 ไม่มีรายการที่มีตำแหน่งที่ตั้ง</p>
          </div>
        )}
      </div>

      {/* Issues List */}
      <div className="issues-list">
        <div className="issues-header">
          <h2>📋 รายการแจ้งทั้งหมด ({filteredIssues.length})</h2>
          <button 
            className="pdf-report-btn"
            onClick={handleGoToReports}
          >
            📄 รายงาน PDF
          </button>
        </div>
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

                {issue.status === 'pending' && (
                  <button 
                    className="fix-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedIssueId(issue.id);
                      setShowFixModal(true);
                    }}
                  >
                    🔧 แจ้งว่าซ่อมแล้ว
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* ---------- Selected Issue Modal ---------- */}
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

      {/* ---------- Fix Modal ---------- */}
      {showFixModal && (
        <div className="modal-overlay" onClick={() => setShowFixModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowFixModal(false)}>✕</button>
            <h3>📸 แจ้งว่าซ่อมแล้ว</h3>
            <p>อัปโหลดภาพหลังซ่อม (ถ่ายรูปใหม่เท่านั้น)</p>
            <label 
              htmlFor="fixFileInput" 
              className="upload-area" 
              style={{ 
                border: '2px dashed #D1D5DB', 
                borderRadius: '8px', 
                padding: '20px', 
                textAlign: 'center', 
                cursor: 'pointer',
                display: 'block'
              }}
            >
              {fixPreview ? (
                <img src={fixPreview} alt="Preview" style={{ maxWidth: '100%', maxHeight: '200px' }} />
              ) : (
                <>
                  <div style={{ fontSize: '40px' }}>📷</div>
                  <p>แตะเพื่อถ่ายรูปหรือเลือกไฟล์</p>
                </>
              )}
              <input 
                type="file" 
                accept="image/*" 
                capture="environment" 
                onChange={handleFixImageChange} 
                style={{ display: 'none' }}
                id="fixFileInput"
              />
            </label>
            <button 
              onClick={handleSubmitFix} 
              disabled={fixing || !fixFile}
              style={{
                width: '100%',
                padding: '12px',
                background: fixing ? '#9CA3AF' : '#06C755',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: 'bold',
                cursor: fixing ? 'not-allowed' : 'pointer',
                marginTop: '12px'
              }}
            >
              {fixing ? 'กำลังส่ง...' : 'ยืนยันการซ่อม'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default IssueDashboard;