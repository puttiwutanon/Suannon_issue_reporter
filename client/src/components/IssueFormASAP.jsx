import React, { useState, useEffect } from 'react';
import liff from '@line/liff';
import './styles/IssueFormASAPStyle.scss';

// Built from the school map (แผนผังโรงเรียนสวนกุหลาบวิทยาลัย นนทบุรี).
// Classroom buildings (สธ 1-6, 9-10) get a required floor picker, since
// they're multi-story and "อาคารเรียน สธ 6" alone isn't specific enough.
// Everything else is a single named spot, so no extra field is needed.
const BUILDING_LOCATIONS = [
  'อาคารเรียน สธ 1', 'อาคารเรียน สธ 2', 'อาคารเรียน สธ 3', 'อาคารเรียน สธ 4',
  'อาคารเรียน สธ 5', 'อาคารเรียน สธ 6', 'อาคารเรียน สธ 9', 'อาคารเรียน สธ 10',
];

const OTHER_LOCATIONS = [
  'สนามฟุตบอล',
  'หอพระ',
  'พระบรมราชานุสาวรีย์รัชกาลที่ 5',
  'ลานอเนกประสงค์',
  'อาคารประชาสัมพันธ์และกิจการนักเรียน',
  'ป้อมยาม',
  'ศูนย์ To Be Number 1',
  'อัฒจันทร์',
  'ห้องน้ำนักเรียน',
  'ศาลากลางน้ำ',
  'สวนเสริมปัญญา',
  'หอประชุมสิรินธราลัย',
  'ห้องสมุด',
  'ศูนย์เกษตรกรรม',
  'บ้านพักครู/บุคลากร',
  'ประตูด้านหลัง',
  'สระน้ำ',
  'สระว่ายน้ำ',
  'ลานจอดรถ',
  'Suannon music studio',
  'Suannon Ceramic',
  'Suannon Learning mall',
  'สวนนนท์ Coffee Shop',
  'ร้านสหกรณ์โรงเรียน',
  'อื่นๆ (โปรดระบุในรายละเอียด)',
];

// One lookup table keyed by building name, instead of a separate
// if-block per building — adding/editing a building's floors is now
// a one-line change here, and it's what actually drives the <select>.
const FLOOR_OPTIONS = {
  'อาคารเรียน สธ 1': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4'],
  'อาคารเรียน สธ 2': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4'],
  'อาคารเรียน สธ 3': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4'],
  'อาคารเรียน สธ 4': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4'],
  'อาคารเรียน สธ 5': ['ชั้น 1', 'ห้องวงโยธวาทิต'],
  'อาคารเรียน สธ 6': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3'],
  'อาคารเรียน สธ 9': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4', 'ชั้น 5'],
  'อาคารเรียน สธ 10': ['ชั้น 1', 'ชั้น 2', 'ชั้น 3', 'ชั้น 4', 'ชั้น 5', 'ชั้น 6', 'ชั้น 7'],
};

export default function IssueFormASAP({ profile, idToken }) {
  const [category, setCategory] = useState('Facilities');
  const [building, setBuilding] = useState('');
  const [floor, setFloor] = useState('');
  const [roomDetail, setRoomDetail] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [location, setLocation] = useState({ lat: null, lng: null });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const isClassroomBuilding = BUILDING_LOCATIONS.includes(building);
  const floorChoices = FLOOR_OPTIONS[building] || [];

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

    // Belt-and-suspenders: `required` on the selects covers most cases,
    // but classroom buildings also need a floor picked.
    if (isClassroomBuilding && !floor) {
      setStatusMsg('❌ กรุณาเลือกชั้นด้วย');
      return;
    }

    setIsSubmitting(true);
    setStatusMsg('กำลังส่งข้อมูล...');

    const locationDetail = isClassroomBuilding
      ? `${building} ${floor}${roomDetail.trim() ? ` ห้อง ${roomDetail.trim()}` : ''}`
      : building;

    const formData = new FormData();
    formData.append('lineIdToken', idToken);
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
      console.log('📤 Sending to:', apiUrl);

      const res = await fetch(`${apiUrl}/api/issues?ngrok-skip-browser-warning=true`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      console.log('📥 Response:', data);

      if (res.ok && data.success) {
        setStatusMsg('✅ แจ้งปัญหาสำเร็จ!');
        setTimeout(() => {
          if (liff.isInClient()) liff.closeWindow();
        }, 1500);
      } else {
        setStatusMsg(`❌ ${data.detail || 'เกิดข้อผิดพลาดในการส่งข้อมูล'}`);
      }
    } catch (err) {
      console.error('❌ Error:', err);
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
            <select
              value={building}
              onChange={(e) => {
                setBuilding(e.target.value);
                setFloor('');
                setRoomDetail('');
              }}
              required
              className="input"
            >
              <option value="" disabled>-- เลือกสถานที่ --</option>
              <optgroup label="อาคารเรียน">
                {BUILDING_LOCATIONS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </optgroup>
              <optgroup label="สถานที่อื่นๆ">
                {OTHER_LOCATIONS.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </optgroup>
            </select>

            {/* The floor picker only makes sense once a classroom
                building with a known floor list is selected — and it
                needs its own <select>, since <optgroup> can't stand
                on its own outside one. */}
            {isClassroomBuilding && floorChoices.length > 0 && (
              <select
                value={floor}
                onChange={(e) => setFloor(e.target.value)}
                required
                className="input"
                style={{ marginTop: '8px' }}
              >
                <option value="" disabled>-- เลือกชั้น --</option>
                {floorChoices.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            )}

            {isClassroomBuilding && floor && (
              <input
                type="text"
                value={roomDetail}
                onChange={(e) => setRoomDetail(e.target.value)}
                className="input"
                style={{ marginTop: '8px' }}
                placeholder="ระบุเลขห้อง (ถ้ามี) เช่น 2301 1402 9303"
              />
            )}
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