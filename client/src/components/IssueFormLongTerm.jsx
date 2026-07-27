import React, { useState } from 'react';
import liff from '@line/liff';

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
    formData.append('category', 'Suggestion');  // fixed category for suggestions
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
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>📝 เสนอแนะเพื่อปรับปรุงโรงเรียน</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.row}>
            <div style={{ flex: 1, marginRight: 8 }}>
              <label style={styles.label}>ชื่อ</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                style={styles.input}
                placeholder="ชื่อ"
              />
            </div>
            <div style={{ flex: 1, marginLeft: 8 }}>
              <label style={styles.label}>นามสกุล</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                style={styles.input}
                placeholder="นามสกุล"
              />
            </div>
          </div>

          <div style={styles.row}>
            <div style={{ flex: 1, marginRight: 8 }}>
              <label style={styles.label}>ชั้นปี</label>
              <input
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                required
                style={styles.input}
                placeholder="เช่น ม.4"
              />
            </div>
            <div style={{ flex: 1, marginLeft: 8 }}>
              <label style={styles.label}>ห้อง</label>
              <input
                type="text"
                value={studentClass}
                onChange={(e) => setStudentClass(e.target.value)}
                required
                style={styles.input}
                placeholder="เช่น 5"
              />
            </div>
            <div style={{ flex: 0.7, marginLeft: 8 }}>
              <label style={styles.label}>เลขที่</label>
              <input
                type="text"
                value={studentNumber}
                onChange={(e) => setStudentNumber(e.target.value)}
                required
                style={styles.input}
                placeholder="เลขที่"
              />
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>ข้อเสนอแนะ / เรื่องที่ต้องการแจ้ง</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows={4}
              style={{ ...styles.input, resize: 'vertical' }}
              placeholder="เขียนข้อเสนอแนะหรือเรื่องที่อยากบอกสภานักเรียน..."
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>แนบภาพประกอบ (ถ้ามี)</label>
            <label style={styles.uploadArea}>
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" style={styles.previewImage} />
              ) : (
                <div style={styles.uploadPlaceholder}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
                  แตะเพื่อแนบภาพ
                </div>
              )}
              <input type="file" accept="image/*" onChange={handleImageChange} style={{ display: 'none' }} />
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              ...styles.submitButton,
              backgroundColor: isSubmitting ? '#9CA3AF' : '#06C755',
            }}
          >
            {isSubmitting ? 'กำลังส่ง...' : 'ส่งข้อเสนอแนะ'}
          </button>
        </form>

        {statusMsg && <p style={styles.statusMsg}>{statusMsg}</p>}
      </div>
    </div>
  );
}

// ---------- Styles ----------
const styles = {
  container: { backgroundColor: '#F3F4F6', minHeight: '100vh', padding: '16px', fontFamily: 'sans-serif' },
  card: { maxWidth: '400px', margin: '0 auto', backgroundColor: '#FFF', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' },
  title: { textAlign: 'center', margin: '0 0 16px 0', color: '#111827', fontSize: '22px' },
  row: { display: 'flex', marginBottom: '12px' },
  field: { marginBottom: '16px' },
  label: { display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: 'bold', color: '#374151' },
  input: { width: '100%', padding: '10px', border: '1px solid #D1D5DB', borderRadius: '8px', fontSize: '15px', backgroundColor: '#F9FAFB', boxSizing: 'border-box' },
  uploadArea: { display: 'block', width: '100%', border: '2px dashed #D1D5DB', borderRadius: '8px', textAlign: 'center', cursor: 'pointer', backgroundColor: '#F9FAFB', overflow: 'hidden' },
  uploadPlaceholder: { padding: '30px 0', color: '#6B7280' },
  previewImage: { width: '100%', height: '200px', objectFit: 'cover' },
  submitButton: { width: '100%', padding: '14px', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 2px 4px rgba(6, 199, 85, 0.2)' },
  statusMsg: { textAlign: 'center', marginTop: '16px', color: '#374151', fontWeight: 'bold' },
};