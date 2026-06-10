import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { guestApi, adminApi, setToken, clearToken } from './api'
import './App.css'

const PUBLIC_WIFI_NAME = 'API-Test-Network WiFi'

// ============================================================================
// COMPONENT 1: THE GUEST PORTAL
// ============================================================================
function GuestPortal() {
  const [formData, setFormData] = useState({ name: '', email: '', duration_hours: 8 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [trackingId, setTrackingId] = useState(null)
  const [status, setStatus] = useState('idle') 
  const [credentials, setCredentials] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await guestApi.post(`/request-access`, {
        name: formData.name,
        email: formData.email,
        duration_hours: parseInt(formData.duration_hours)
      })
      setTrackingId(res.data.id)
      setStatus('pending')
    } catch (err) {
      setError('Failed to submit request to server.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let interval;
    if (status === 'pending' && trackingId) {
      interval = setInterval(async () => {
        try {
          const res = await guestApi.get(`/request-status/${trackingId}`)
          const currentStatus = res.data.status
          
          if (currentStatus === 'Active') {
            setStatus('active')
            setCredentials({
              email: res.data.email,
              password: res.data.password,
              expires: new Date(res.data.expires_at).toLocaleString()
            })
            clearInterval(interval) 
          } else if (currentStatus === 'Rejected') {
            setStatus('rejected')
            clearInterval(interval)
          }
        } catch (e) {
          console.error("Polling error", e)
        }
      }, 3000) 
    }
    return () => clearInterval(interval) 
  }, [status, trackingId])

  const getWifiQRString = () => `WIFI:T:WPA;S:${PUBLIC_WIFI_NAME};P:${credentials?.password};;`

  return (
    <div className="card">
      {status === 'idle' && (
        <>
          <h2 style={{marginTop: 0}}>Request Wi-Fi Access</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Full Name</label>
              <input type="text" name="name" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Email Address</label>
              <input type="email" name="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Time Required</label>
              <select name="duration_hours" value={formData.duration_hours} onChange={(e) => setFormData({...formData, duration_hours: e.target.value})}>
                <option value="1">1 Hour</option>
                <option value="4">4 Hours</option>
                <option value="8">8 Hours</option>
              </select>
            </div>
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Submitting...' : 'Request Access'}
            </button>
          </form>
          {error && <div className="status-badge error" style={{marginTop: '15px'}}>{error}</div>}
        </>
      )}

      {status === 'pending' && (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <h2>Request Sent!</h2>
          <p style={{ color: 'var(--text-muted)' }}>Waiting for Administrator Approval...</p>
          <div className="loader" style={{ marginTop: '20px', fontSize: '2rem' }}>⏳</div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '20px' }}>This page will automatically update.</p>
        </div>
      )}

      {status === 'active' && credentials && (
        <div className="credentials-card" style={{ padding: '20px', borderRadius: '12px', border: '1px solid var(--accent-green)' }}>
          <h2>🎉 Access Granted</h2>
          <p style={{ color: 'var(--text-muted)' }}>Scan the code to connect.</p>
          
          <div className="qr-container">
            <QRCodeSVG value={getWifiQRString()} size={180} level={"H"} includeMargin={false} />
          </div>

          <div className="details-box" style={{ textAlign: 'left', margin: '20px 0', padding: '15px', backgroundColor: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <p style={{ margin: '5px 0' }}><strong>Network:</strong> {PUBLIC_WIFI_NAME}</p>
            <p style={{ margin: '5px 0' }}><strong>Login Username:</strong> {credentials.email}</p>
            <p style={{ margin: '15px 0 5px 0' }}><strong>Password:</strong> <br/><span className="password-display" style={{ marginTop: '8px', display: 'inline-block' }}>{credentials.password}</span></p>
          </div>
          
          <button className="btn-neutral" onClick={() => window.location.reload()} style={{width: '100%'}}>
            Done
          </button>
        </div>
      )}

      {status === 'rejected' && (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <h2 style={{ color: 'var(--accent-red)' }}>Access Denied</h2>
          <p style={{ color: 'var(--text-muted)' }}>The administrator has rejected this request.</p>
          <button className="btn-neutral" onClick={() => setStatus('idle')} style={{marginTop: '20px'}}>Try Again</button>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// COMPONENT 2: THE ADMIN DASHBOARD
// ============================================================================
function AdminPortal() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isAuthChecking, setIsAuthChecking] = useState(true)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')

  const [guests, setGuests] = useState([])
  const [activeTab, setActiveTab] = useState('queue')

  // Validation Check on Boot
  useEffect(() => {
    adminApi.get('/admin/me')
      .then(() => setIsAuthenticated(true))
      .catch(() => {
        clearToken()
        setIsAuthenticated(false)
      })
      .finally(() => setIsAuthChecking(false))
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    
    const params = new URLSearchParams()
    params.append('username', loginForm.username)
    params.append('password', loginForm.password)

    try {
      const res = await guestApi.post('/admin/login', params)
      setToken(res.data.access_token) // Secure memory storage
      setIsAuthenticated(true)
      fetchGuests()
    } catch (err) {
      setLoginError('Invalid username or password')
    }
  }

  const handleLogout = () => {
    clearToken()
    setIsAuthenticated(false)
  }

  const fetchGuests = async () => {
    try { 
        const r = await adminApi.get(`/guests`); 
        setGuests(r.data); 
    } catch (e) { console.error("Database fetch failed", e) } 
  }

  useEffect(() => { 
      let i;
      if (isAuthenticated) {
        fetchGuests(); 
        i = setInterval(fetchGuests, 3000); 
      }
      return () => clearInterval(i) 
  }, [isAuthenticated])

  const handleApprove = async (id) => {
    try { await adminApi.post(`/approve-request/${id}`); fetchGuests(); } 
    catch (error) { alert(`Cisco API Error: ${error.response?.data?.detail || error.message}`); }
  }

  const handleReject = async (id) => {
    try { await adminApi.delete(`/reject-request/${id}`); fetchGuests(); } 
    catch (error) { alert("Failed to reject request."); }
  }
  
  const handleRevoke = async (id) => {
    try { await adminApi.delete(`/revoke-guest/${id}`); fetchGuests(); } 
    catch (error) { alert("Failed to revoke guest."); }
  }

  if (isAuthChecking) return <div className="card" style={{textAlign: 'center'}}><h2>Loading...</h2></div>

  if (!isAuthenticated) {
    return (
      <div className="card">
        <h2 style={{marginTop: 0, textAlign: 'center'}}>Admin Portal</h2>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Username</label>
            <input type="text" onChange={(e) => setLoginForm({...loginForm, username: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" onChange={(e) => setLoginForm({...loginForm, password: e.target.value})} required />
          </div>
          <button type="submit" className="btn-submit">Sign In</button>
          {loginError && <div className="status-badge error" style={{marginTop: '15px'}}>{loginError}</div>}
        </form>
      </div>
    )
  }

  const pending = guests.filter(g => g.status === 'Pending')
  const ledger = guests.filter(g => g.status !== 'Pending')

  return (
    <div className="card">
        <div className="dashboard-header">
          <h2 style={{ margin: 0 }}>Dashboard</h2>
          <button onClick={handleLogout} className="btn-logout">Sign Out</button>
        </div>
        
        <div className="tabs-container">
            <button className={`tab-btn ${activeTab === 'queue' ? 'active' : ''}`} onClick={() => setActiveTab('queue')}>Queue ({pending.length})</button>
            <button className={`tab-btn ${activeTab === 'ledger' ? 'active' : ''}`} onClick={() => setActiveTab('ledger')}>Ledger</button>
        </div>
        
        {activeTab === 'queue' ? (
            <table className="data-table">
                <thead>
                    <tr><th>Name</th><th>Email</th><th>Action</th></tr>
                </thead>
                <tbody>
                {pending.map(g => (
                    <tr key={g.id}>
                        <td>{g.name}</td>
                        <td>{g.email}</td>
                        <td>
                            <button style={{backgroundColor: 'var(--accent-green)', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', marginRight: '5px', cursor: 'pointer'}} onClick={() => handleApprove(g.id)}>Approve</button>
                            <button className="btn-revoke-small" onClick={() => handleReject(g.id)}>Deny</button>
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        ) : (
            <table className="data-table">
                <thead>
                    <tr><th>Name</th><th>Status</th><th>Expires At</th><th>Action</th></tr>
                </thead>
                <tbody>
                {ledger.map(g => (
                    <tr key={g.id}>
                        <td>{g.name}</td>
                        <td>{g.status}</td>
                        <td>{g.expires_at ? new Date(g.expires_at).toLocaleString() : 'N/A'}</td>
                        <td>
                          {g.status === 'Active' && <button className="btn-revoke-small" onClick={() => handleRevoke(g.id)}>Revoke</button>}
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        )}
    </div>
  )
}

// ============================================================================
// ROOT APPLICATION CONTROLLER
// ============================================================================
function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))

  return (
    <Router>
      <div className="container">
        <div className="top-bar">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>

        <div className="header">
          <h1>NetPass Gateway</h1>
          <p>Enterprise Zero-Trust Wireless Provisioning</p>
        </div>

        <Routes>
          <Route path="/" element={<GuestPortal />} />
          <Route path="/admin" element={<AdminPortal />} />
        </Routes>
        
        <div style={{ textAlign: 'center', marginTop: '40px', fontSize: '0.8rem', opacity: 0.5 }}>
           <Link to="/" style={{ color: 'var(--text-primary)', marginRight: '15px' }}>Guest View</Link> 
           | 
           <Link to="/admin" style={{ color: 'var(--text-primary)', marginLeft: '15px' }}>Admin View</Link>
        </div>
      </div>
    </Router>
  )
}

export default App