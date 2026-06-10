import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export const guestApi = axios.create({
  baseURL: API_BASE
})

export const adminApi = axios.create({
  baseURL: API_BASE
})

// Memory-only token storage (Prevents XSS Vulnerabilities)
let _token = null

export const setToken = (t) => { _token = t }
export const clearToken = () => { _token = null }

// Request Interceptor: Attach token to every admin request
adminApi.interceptors.request.use((config) => {
  if (_token) config.headers.Authorization = `Bearer ${_token}`
  return config
})

// Global Response Interceptor: Catch expired sessions mid-flight
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect if we HAD a token (expired session). 
    // Prevents infinite reload loop on initial boot check.
    if (error.response?.status === 401 && _token) {
      clearToken()
      window.location.href = '/admin' 
    }
    return Promise.reject(error)
  }
)