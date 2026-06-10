import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { QRCodeSVG } from 'qrcode.react'
import './App.css'

const API_BASE = 'http://localhost:8000'
const PUBLIC_WIFI_NAME = 'API-Test-Network WiFi'
// ============================================================================
// COMPONENT 1: THE GUEST PORTAL (URL: / )
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
      const res = await axios.post(`${API_BASE}/request-access`, formData)
      setTrackingId(res.data.id)
      setStatus('pending')
    } catch (err) {
      setError('Failed to reach backend. Check server logs.')
    } finally {
      setLoading(false)
    }
  }

  // Automated Polling Loop
  useEffect(() => {
    let interval;
    if (status === 'pending' && trackingId) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/request-status/${trackingId}`)
          if (res.data.status === 'Active') {
            setStatus('active')
            // FIX: We now capture the email from the backend
            setCredentials({ 
                email: res.data.email, 
                password: res.data.password, 
                expires: new Date(res.data.expires_at).toLocaleString() 
            })
            clearInterval(interval)
          } else if (res.data.status === 'Rejected') {
            setStatus('rejected')
            clearInterval(interval)
          }
        } catch (e) { console.error("Polling error", e) }
      }, 3000)
    }
    return () => clearInterval(interval)
  }, [status, trackingId])

  return (
    <div className="card">
      {status === 'idle' && (
        <form onSubmit={handleSubmit}>
          <div className="form-group"><label>Full Name</label><input type="text" onChange={(e) => setFormData({...formData, name: e.target.value})} required/></div>
          <div className="form-group"><label>Email</label><input type="email" onChange={(e) => setFormData({...formData, email: e.target.value})} required/></div>
          <div className="form-group"><label>Duration</label>
            <select onChange={(e) => setFormData({...formData, duration_hours: e.target.value})}>
                <option value="1">1 Hour</option><option value="4">4 Hours</option><option value="8">8 Hours</option>
            </select>
          </div>
          <button className="btn-submit" disabled={loading}>{loading ? 'Submitting...' : 'Request Access'}</button>
          {error && <div className="status-badge error" style={{marginTop: '15px'}}>{error}</div>}
        </form>
      )}
      
      {status === 'pending' && <div style={{textAlign:'center', padding: '40px'}}><h2>⏳ Request Sent</h2><p>Waiting for admin approval...</p></div>}
      
      {status === 'active' && (
        <div className="credentials-card">
          <h2>🎉 Access Granted</h2>
          <div className="qr-container"><QRCodeSVG value={`WIFI:T:WPA;S:${PUBLIC_WIFI_NAME};P:${credentials.password};;`} size={180}/></div>
          
          <div className="details-box" style={{ textAlign: 'left', margin: '20px 0', padding: '15px', backgroundColor: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <p style={{ margin: '5px 0' }}><strong>Network:</strong> {PUBLIC_WIFI_NAME}</p>
            {/* FIX: Explicitly tell the user what email to use in the portal */}
            <p style={{ margin: '5px 0' }}><strong>Login Username:</strong> {credentials.email}</p>
            <p style={{ margin: '15px 0 5px 0' }}><strong>Password:</strong> <br/><span className="password-display" style={{ marginTop: '8px', display: 'inline-block' }}>{credentials.password}</span></p>
          </div>
          
          <button className="btn-neutral" onClick={() => window.location.reload()} style={{width: '100%'}}>Done</button>
        </div>
      )}
    </div>
  )
}
// ============================================================================
// COMPONENT 2: THE ADMIN DASHBOARD (URL: /admin )
// ============================================================================
function AdminPortal() {
  const [guests, setGuests] = useState([])
  const [activeTab, setActiveTab] = useState('queue')

  const fetchGuests = async () => {
    try { 
        const r = await axios.get(`${API_BASE}/guests`); 
        setGuests(r.data); 
    } catch (e) { console.error("Database fetch failed", e) }
  }

  useEffect(() => { 
      const i = setInterval(fetchGuests, 3000); 
      fetchGuests(); 
      return () => clearInterval(i) 
  }, [])

  const handleApprove = async (id) => {
    try {
        await axios.post(`${API_BASE}/approve-request/${id}`);
        fetchGuests();
    } catch (error) {
        alert(`Cisco API Error: ${error.response?.data?.detail || error.message}`);
    }
  }

  // --- ADD THIS FUNCTION ---
  const handleReject = async (id) => {
    try {
        await axios.delete(`${API_BASE}/reject-request/${id}`);
        fetchGuests();
    } catch (error) {
        alert("Failed to reject request.");
    }
  }
  
  const pending = guests.filter(g => g.status === 'Pending')
  const ledger = guests.filter(g => g.status !== 'Pending')

  return (
    <div className="card">
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
                            <button style={{backgroundColor: 'var(--accent-green)', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', marginRight: '5px'}} onClick={() => handleApprove(g.id)}>Approve</button>
                            <button className="btn-revoke-small" onClick={() => handleReject(g.id)}>Deny</button>
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        ) : (
            <table className="data-table">
                <thead>
                    <tr><th>Name</th><th>Status</th><th>Password</th></tr>
                </thead>
                <tbody>
                {ledger.map(g => (
                    <tr key={g.id}>
                        <td>{g.name}</td>
                        <td>{g.status}</td>
                        <td>{g.password || 'N/A'}</td>
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
          {/* Default Route: The locked-down Guest interface */}
          <Route path="/" element={<GuestPortal />} />
          
          {/* Admin Route: The secure backend interface */}
          <Route path="/admin" element={<AdminPortal />} />
        </Routes>
        
        {/* Hidden Footer Links for Navigation testing */}
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