import React, { useState, useEffect, useMemo } from 'react';
import liff from '@line/liff';
import './styles/IssueCheckStyle.scss';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// ---------- Logger ----------
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

// ---------- School Coordinates ----------
const SCHOOL_COORDS = {
  lat: 13.910305,
  lng: 100.512396,
};

const SCHOOL_BOUNDS = {
  north: 13.9130,
  south: 13.9076,
  east: 100.5156,
  west: 100.5092,
};

// ---------- Fix for default marker icons ----------
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ---------- Status labels (must match IssueDashboard.jsx) ----------
// pending      -> just submitted, nobody's looked at it yet
// acknowledged -> team has seen it and is on it
// in_progress  -> team is actively fixing, progress photo attached
// resolved     -> done
const STATUS_LABELS = {
  pending: { text: '⏳ รอดำเนินการ', className: 'pending' },
  acknowledged: { text: '📨 ทีมงานรับเรื่องแล้ว', className: 'acknowledged' },
  in_progress: { text: '🔧 กำลังดำเนินการซ่อม', className: 'in_progress' },
  resolved: { text: '✅ เสร็จสิ้น', className: 'resolved' },
};
function getStatusLabel(status) {
  return STATUS_LABELS[status] || STATUS_LABELS.pending;
}

// ---------- Custom Marker Icon ----------
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

// ---------- FitBounds Component ----------
function FitBounds({ markers }) {
  const map = useMap();
  useEffect(() => {
    if (markers && markers.length > 0) {
      const bounds = L.latLngBounds(markers.map(m => [m.latitude, m.longitude]));
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [markers, map]);
  return null;
}

// ---------- Main Component ----------
export default function IssueCheck({ profile, viewMode, idToken }) {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mapKey, setMapKey] = useState(0);

  const locatedIssues = useMemo(
    () => issues.filter(issue => issue.latitude && issue.longitude),
    [issues]
  );

  useEffect(() => {
    if (viewMode === 'view_others' && locatedIssues.length > 0) {
      setMapKey(Date.now());
    }
  }, [locatedIssues, viewMode]);  

  useEffect(() => {
    const fetchIssues = async () => {
      logger.info(`🚀 Fetching issues started - ViewMode: ${viewMode}`);
      logger.debug(`👤 Profile:`, { userId: profile.userId, displayName: profile.displayName });

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        logger.debug(`📡 API URL from env: ${apiUrl}`);
        
        let url = `${apiUrl}/api/issues/community?view_mode=${viewMode === 'view_mine' ? 'mine' : 'others'}`;
        logger.debug(`🔗 Final URL: ${url}`);

        const startTime = Date.now();
        logger.info(`⏳ Sending request...`);

        const res = await fetch(url, {
          headers: { 
            'x-line-id-token': idToken,
            'ngrok-skip-browser-warning': 'true'
          },
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
          setIssues(data.issues);
          logger.success(`✅ Set ${data.issues.length} issues in state`);
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
        logger.info(`🏁 Fetch completed`);
      }
    };

    fetchIssues();
  }, [profile, viewMode, idToken]);


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

      {viewMode === 'view_others' && locatedIssues.length > 0 && (
        <div className="map-container" style={{ height: '300px', marginBottom: '16px', borderRadius: '8px', overflow: 'hidden' }}>
        <MapContainer
          key={mapKey}
          center={SCHOOL_COORDS}
          zoom={17}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
          scrollWheelZoom={true}
          dragging={true}
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution='&copy; <a href="https://www.esri.com">Esri</a>'
            maxZoom={19}
          />

          {/* Add the same landmark the dashboard has */}
          <Marker
            position={[SCHOOL_COORDS.lat, SCHOOL_COORDS.lng]}
            icon={L.divIcon({
              className: 'school-marker',
              html: `<div style="background-color:#3B82F6;color:white;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:12px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);">🏫</div>`,
              iconSize: [20, 20],
              iconAnchor: [10, 10],
            })}
          >
            <Popup>🏫 โรงเรียน</Popup>
          </Marker>

          {locatedIssues.map((issue) => (
            <Marker key={issue.id} position={[issue.latitude, issue.longitude]} icon={getMarkerIcon(issue.issueType)}>
              <Popup>...</Popup>
            </Marker>
          ))}

          {/* Only auto-fit when there are enough points that it's meaningful */}
          {locatedIssues.length > 1 && <FitBounds markers={locatedIssues} />}
        </MapContainer>
        </div>
      )}

      {issues.length === 0 ? (
        <div className="empty">ยังไม่มีเรื่องแจ้งในหมวดนี้</div>
      ) : (
        <>
          {/* ---------- Card View ---------- */}
          {issues.map((issue) => {
            const statusLabel = getStatusLabel(issue.status);
            return (
              <div key={issue.id} className="card">
                <div className="card-header">
                  <span className="category">#{issue.category}</span>
                  <span className={`status ${statusLabel.className}`}>
                    {statusLabel.text}
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
                    {issue.progressImageUrl && (
                      <img src={issue.progressImageUrl} alt="กำลังซ่อม" className="thumb" />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}