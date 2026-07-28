import React, { useState } from 'react';
import liff from '@line/liff';
import './styles/IssueFormLongTermStyle.scss';

export default function IssueFormLongTerm({ profile }) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [year, setYear] = useState('');
  const [studentClass, setStudentClass] = useState('');
  const [studentNumber, setStudentNumber] = useState('');
  const [message, setMessage] = useState('');
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

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
    formData.append('reporterName', `${firstName} ${lastName}`);
    formData.append('category', 'Suggestion');
    formData.append('description', message);
    formData.append('studentYear', year);
    formData.append('studentClass', studentClass);
    formData.append('studentNumber', studentNumber);
    if (file) formData.append('image', file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/issues`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMsg('✅ ส่งคำแนะนำสำเร็จ!');
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
        <h2 className="title">📝 เสนอแนะเพื่อปรับปรุงโรงเรียน</h2>
        <form onSubmit={handleSubmit}>
          <div className="row">
            <div className="col">
              <label className="label">ชื่อ</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                className="input"
                placeholder="ชื่อ"
              />
            </div>
            <div className="col">
              <label className="label">นามสกุล</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                className="input"
                placeholder="นามสกุล"
              />
            </div>
          </div>

          <div className="row">
            <div className="col">
              <label className="label">ชั้นปี</label>
              <input
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                required
                className="input"
                placeholder="เช่น ม.4"
              />
            </div>
            <div className="col">
              <label className="label">ห้อง</label>
              <input
                type="text"
                value={studentClass}
                onChange={(e) => setStudentClass(e.target.value)}
                required
                className="input"
                placeholder="เช่น 5"
              />
            </div>
            <div className="col small">
              <label className="label">เลขที่</label>
              <input
                type="text"
                value={studentNumber}
                onChange={(e) => setStudentNumber(e.target.value)}
                required
                className="input"
                placeholder="เลขที่"
              />
            </div>
          </div>

          <div className="field">
            <label className="label">ข้อเสนอแนะ / เรื่องที่ต้องการแจ้ง</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows={4}
              className="input textarea"
              placeholder="เขียนข้อเสนอแนะหรือเรื่องที่อยากบอกสภานักเรียน..."
            />
          </div>

          <div className="field">
            <label className="label">แนบภาพประกอบ (ถ้ามี)</label>
            <label className="upload-area">
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" className="preview-image" />
              ) : (
                <div className="upload-placeholder">
                  <div className="icon">📷</div>
                  แตะเพื่อแนบภาพ
                </div>
              )}
              <input type="file" accept="image/*" onChange={handleImageChange} style={{ display: 'none' }} />
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={`submit-btn ${isSubmitting ? 'disabled' : 'default'}`}
          >
            {isSubmitting ? 'กำลังส่ง...' : 'ส่งข้อเสนอแนะ'}
          </button>
        </form>

        {statusMsg && <p className="status-msg">{statusMsg}</p>}
      </div>
    </div>
  );
}