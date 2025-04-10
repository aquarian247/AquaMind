/**
 * API Authentication Utility
 * 
 * This utility handles token authentication for all API requests.
 * It ensures a consistent approach to including authentication tokens in requests.
 */

import axios from 'axios'

/**
 * Set up an axios instance with authentication interceptors
 * @returns {import('axios').AxiosInstance} Authenticated axios instance
 */
export function createAuthenticatedAxios() {
  const instance = axios.create({
    baseURL: '/api/v1/',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  })

  // Add request interceptor to include token in all requests
  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Token ${token}`
    }
    return config
  })

  // Make sure URLs have trailing slashes for Django URL patterns
  instance.interceptors.request.use((config) => {
    if (!config.url.endsWith('/') && !config.url.includes('?')) {
      config.url = `${config.url}/`
    }
    return config
  })

  return instance
}

/**
 * Get the current auth token
 * @returns {string|null} The current token or null if not found
 */
export function getAuthToken() {
  return localStorage.getItem('token')
}

/**
 * Set the auth token in localStorage and update axios defaults
 * @param {string} token The token to set
 */
export function setAuthToken(token) {
  if (!token) return false
  
  try {
    localStorage.setItem('token', token)
    // Update axios defaults
    axios.defaults.headers.common['Authorization'] = `Token ${token}`
    return true
  } catch (error) {
    console.error('Error setting token:', error)
    return false
  }
}

/**
 * Apply the auth token to an axios instance directly
 * @param {import('axios').AxiosInstance} axiosInstance The axios instance to configure
 */
export function applyTokenToAxios(axiosInstance) {
  const token = getAuthToken()
  if (token && axiosInstance) {
    axiosInstance.defaults.headers.common['Authorization'] = `Token ${token}`
    return true
  }
  return false
}

/**
 * Apply the auth token to all axios instances
 */
export function applyTokenGlobally() {
  const token = getAuthToken()
  if (token) {
    // Apply to axios defaults
    axios.defaults.headers.common['Authorization'] = `Token ${token}`
    
    // Apply to any registered axios instances
    if (typeof window !== 'undefined' && window.__axiosInstances) {
      window.__axiosInstances.forEach(instance => {
        if (instance && instance.defaults) {
          instance.defaults.headers.common['Authorization'] = `Token ${token}`
        }
      })
    }
    return true
  }
  return false
}

/**
 * Expose the global API authentication utility
 */
export default {
  createAuthenticatedAxios,
  getAuthToken,
  setAuthToken,
  applyTokenToAxios,
  applyTokenGlobally
}
