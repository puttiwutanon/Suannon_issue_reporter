import React, { useState, useEffect } from 'react';
import liff from '@line/liff';
import './styles/IssueFormASAPStyle.scss';

export default function IssueFormASAP({ profile }) {
  const [category, setCategory] = useState('Facilities');
  const [locationDetail, setLocationDetail] = useState('');
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

  async function compressImage(file, maxWidth = 1280, quality = 0.7) {
    const img = await createImageBitmap(file);
    const scale = Math.min(1, maxWidth / img.width);
    const canvas = document.createElement('canvas');
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(new File([blob], 'photo.jpg', { type: 'image/jpeg' })), 'image/jpeg', quality);
    });
  }

  const handleImageChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const compressed = await compressImage(selectedFile);
      setFile(compressed);
      setPreviewUrl(URL.createObjectURL(compressed));
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
    const fullDescription = `สถานที่: ${locationDetail}\nรายละเอียด: ${description}`;
    formData.append('description', fullDescription);
    formData.append('issue_type', 'urgent');

    if (location.lat) formData.append('latitude', location.lat);
    if (location.lng) formData.append('longitude', location.lng);
    if (file) formData.append('image', file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/issues?ngrok-skip-browser-warning=true`, {
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
    <div className="container">
      <div className="card">
        <h2 className="title">🚨 แจ้งปัญหาโรงเรียน</h2>
        <div className="reporter">
          ผู้แจ้ง: <strong>{profile.displayName}</strong>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label">หมวดหมู่ปัญหา</label>
            <select 
              value={category} 
              onChange={(e) => setCategory(e.target.value)} 
              className="input"
            >
              <option value="Facilities">🪑 อาคารสถานที่</option>
              <option value="Electrical">💡 อุปกรณ์เครื่องใช้ชำรุด</option>
              <option value="Cleanliness">✨ ความสะอาด</option>
              <option value="Others"> 🖥️ อื่นๆ / others</option>
            </select>
          </div>

          <div className="field">
            <label className="label">สถานที่ที่พบปัญหา</label>
            <textarea
              value={locationDetail}
              onChange={(e) => setLocationDetail(e.target.value)}
              required
              rows={2}
              className="input textarea"
              placeholder="ระบุสถานที่หรือห้องที่พบปัญหา เช่น ห้อง10402, ห้องน้ำชายตึก10 ชั้น 5..."
            />
          </div>

          <div className="field">
            <label className="label">รายละเอียด</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={3}
              className="input textarea"
              placeholder="อธิบายปัญหาที่พบเจอ..."
            />
          </div>

          <div className="field">
            <label className="label">ภาพถ่ายประกอบ</label>
            <label className="upload-area">
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" className="preview-image" />
              ) : (
                <div className="upload-placeholder">
                  <div className="icon">📷</div>
                  แตะเพื่อถ่ายรูป
                </div>
              )}
              <input 
                type="file" 
                accept="image/*" 
                capture="environment"   // <-- Forces camera, no gallery
                onChange={handleImageChange} 
                style={{ display: 'none' }} 
              />
            </label>
          </div>

          <div className="location-box">
            <span className="pin">📍</span>
            {location.lat 
              ? `ตำแหน่งของคุณ: ${location.lat.toFixed(5)}, ${location.lng.toFixed(5)}` 
              : 'กำลังค้นหาตำแหน่ง...'
            }
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={`submit-btn ${isSubmitting ? 'disabled' : 'default'}`}
          >
            {isSubmitting ? 'กำลังส่งข้อมูล...' : 'ส่งข้อมูลแจ้งปัญหา'}
          </button>
        </form>

        {statusMsg && <p className="status-msg">{statusMsg}</p>}
      </div>
    </div>
  );
}