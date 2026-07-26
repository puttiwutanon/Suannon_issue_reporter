import React, { useState, useEffect } from 'react';
import liff from '@line/liff';

export default function IssueFormASAP({ profile }) {
  const [category, setCategory] = useState('Facilities');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [location, setLocation] = useState({ lat: null, lng: null });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        (err) => console.warn('Geolocation error:', err)
      );
    }
  }, []);

  const handleImageChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMsg('กำลังส่งข้อมูล...');

    const formData = new FormData();
    formData.append('lineUserId', profile.userId);
    formData.append('reporterName', profile.displayName);
    formData.append('category', category);
    formData.append('description', description);
    
    if (location.lat) formData.append('latitude', location.lat);
    if (location.lng) formData.append('longitude', location.lng);
    if (file) formData.append('image', file);

    try {
      const res = await fetch('http://localhost:8000/api/issues', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMsg('✅ แจ้งปัญหาสำเร็จ!');
        setTimeout(() => {
          if (liff.isInClient()) liff.closeWindow();
        }, 1500);
      } else {
        setStatusMsg('❌ เกิดข้อผิดพลาดในการส่งข้อมูล');
      }
    } catch (err) {
      console.error(err);
      setStatusMsg('❌ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ backgroundColor: '#F3F4F6', minHeight: '100vh', padding: '16px', fontFamily: 'sans-serif' }}>
      <div style={{ maxWidth: '400px', margin: '0 auto', backgroundColor: '#FFFFFF', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
        
        <h2 style={{ textAlign: 'center', margin: '0 0 16px 0', color: '#111827', fontSize: '22px' }}>
          🚨 แจ้งปัญหาโรงเรียน
        </h2>
        
        <div style={{ textAlign: 'center', marginBottom: '20px', fontSize: '14px', color: '#6B7280' }}>
          ผู้แจ้ง: <strong>{profile.displayName}</strong>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Category Selection */}
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>หมวดหมู่ปัญหา</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle}>
              <option value="Facilities">🪑 อาคารสถานที่ / เฟอร์นิเจอร์</option>
              <option value="Electrical">💡 ไฟฟ้า / แอร์ / น้ำประปา</option>
              <option value="Restroom">🚽 ห้องน้ำ / ความสะอาด</option>
              <option value="IT">💻 คอมพิวเตอร์ / Wi-Fi</option>
            </select>
          </div>

          {/* Description */}
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>รายละเอียด</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={3}
              style={{ ...inputStyle, resize: 'none' }}
              placeholder="อธิบายปัญหาที่พบเจอ..."
            />
          </div>

          {/* Image Upload (Traffy Fondue Style) */}
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>ภาพถ่ายประกอบ</label>
            <label style={uploadAreaStyle}>
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" style={{ width: '100%', height: '200px', objectFit: 'cover', borderRadius: '8px' }} />
              ) : (
                <div style={{ color: '#6B7280', padding: '40px 0' }}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>📷</div>
                  แตะเพื่อถ่ายรูปหรือเลือกไฟล์
                </div>
              )}
              {/* Hidden actual file input */}
              <input type="file" accept="image/*" onChange={handleImageChange} style={{ display: 'none' }} />
            </label>
          </div>

          {/* GPS Location */}
          <div style={{ marginBottom: '24px', padding: '12px', backgroundColor: '#F9FAFB', borderRadius: '8px', fontSize: '13px', color: '#4B5563', display: 'flex', alignItems: 'center' }}>
            <span style={{ fontSize: '18px', marginRight: '8px' }}>📍</span>
            {location.lat ? `ตำแหน่งของคุณ: ${location.lat.toFixed(5)}, ${location.lng.toFixed(5)}` : 'กำลังค้นหาตำแหน่ง...'}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: '100%', padding: '14px', backgroundColor: isSubmitting ? '#9CA3AF' : '#06C755', 
              color: '#fff', border: 'none', borderRadius: '8px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(6, 199, 85, 0.2)'
            }}
          >
            {isSubmitting ? 'กำลังส่งข้อมูล...' : 'ส่งข้อมูลแจ้งปัญหา'}
          </button>
        </form>

        {statusMsg && (
          <p style={{ textAlign: 'center', marginTop: '16px', color: '#374151', fontWeight: 'bold' }}>
            {statusMsg}
          </p>
        )}
      </div>
    </div>
  );
}

// Reusable Styles
const labelStyle = { display: 'block', marginBottom: '6px', fontSize: '14px', fontWeight: 'bold', color: '#374151' };
const inputStyle = { width: '100%', padding: '12px', border: '1px solid #D1D5DB', borderRadius: '8px', fontSize: '15px', backgroundColor: '#F9FAFB', boxSizing: 'border-box' };
const uploadAreaStyle = { 
  display: 'block', width: '100%', border: '2px dashed #D1D5DB', borderRadius: '8px', 
  textAlign: 'center', cursor: 'pointer', backgroundColor: '#F9FAFB', boxSizing: 'border-box', overflow: 'hidden'
};