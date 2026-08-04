import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { doSignInWithEmailAndPassword } from '../../firebase/auth.js';
import '../styles/AdminLoginStyle.scss';

function AdminLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const userCredential = await doSignInWithEmailAndPassword(email, password);
      console.log('✅ Logged in user:', userCredential.user.email);
      
      // Store login state
      sessionStorage.setItem('admin_logged_in', 'true');
      
      // Redirect to dashboard
      navigate('/admin/dashboard');
    } catch (err) {
      console.error('❌ Login error:', err);
      setError('❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo"><img src="/src/assets/skn_1 (2).png" alt="" width="150" height="150" /></div>
          <h1>SKN Issue Reporter</h1>
          <p>แผงควบคุมผู้ดูแลระบบ</p>
        </div>

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>อีเมล</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="กรุณาใส่อีเมล"
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label>รหัสผ่าน</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="กรุณาใส่รหัสผ่าน"
              autoComplete="current-password"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? 'กำลังเข้าสู่ระบบ...' : 'เข้าสู่ระบบ'}
          </button>
        </form>

        <div className="login-footer">
          <p>เข้าสู่ระบบด้วยอีเมลที่ลงทะเบียนไว้</p>
          <small>สำหรับคณะกรรมการสภานักเรียนและผู้ดูแลระบบ</small>
        </div>
      </div>
    </div>
  );
}

export default AdminLogin;