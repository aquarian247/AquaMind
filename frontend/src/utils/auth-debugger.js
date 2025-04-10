/**
 * Auth Debugging Utility
 * 
 * This file provides utilities to help debug authentication issues.
 * It's only meant for development environments.
 */

import axios from 'axios'
import { getAuthToken, setAuthToken, applyTokenGlobally } from './api-auth'

/**
 * Sets up the axios defaults with the current token
 */
export function setupAxiosDefaults() {
  const token = localStorage.getItem('token')
  if (token) {
    console.log('Setting global axios Authorization header with token')
    axios.defaults.headers.common['Authorization'] = `Token ${token}`
  } else {
    console.warn('No token found for axios defaults')
  }
}

/**
 * Check if there's a valid auth token in localStorage
 * @returns {string|null} The token or null
 */
export function checkAuthToken() {
  const token = localStorage.getItem('token')
  if (token) {
    console.log('Token found in localStorage:', token.substring(0, 6) + '...' + token.substring(token.length - 6))
    return token
  } else {
    console.warn('No token found in localStorage')
    return null
  }
}

/**
 * Try to refresh the dev auth token
 * @returns {Promise<string|null>} The new token or null if failed
 */
export async function refreshDevToken() {
  try {
    console.log('Attempting to refresh dev token')
    const response = await axios.get('/api/v1/auth/dev-auth/')
    
    if (response.data && response.data.token) {
      // Store the token in local storage
      localStorage.setItem('token', response.data.token)
      console.log('Dev token refreshed and stored')
      
      // Apply token to axios defaults
      setupAxiosDefaults()
      return response.data.token
    }
    console.warn('No token received from dev-auth endpoint')
    return null
  } catch (error) {
    console.error('Error fetching dev auth token:', error)
    return null
  }
}

/**
 * Clears the authentication token
 */
export function clearToken() {
  localStorage.removeItem('token')
  console.log('Token cleared')
  
  // Also clear from axios defaults
  delete axios.defaults.headers.common['Authorization']
  return true
}

// Alias for clearToken to maintain API compatibility
export function clearAuthToken() {
  return clearToken()
}

/**
 * Sets a test token for development
 * @returns {boolean} True if successful
 */
export function setTestToken() {
  const testToken = '9ef45d8bce96a6a41fcba52220c047d6df634ce2' // Example token
  localStorage.setItem('token', testToken)
  console.log('Test token set')
  
  // Apply the token globally to all axios instances
  applyTokenGlobally()
  return true
}

/**
 * Tests an API endpoint with the current token
 * @param {string} endpoint - The API endpoint to test
 * @returns {Promise<Object>} The test result
 */
export async function testEndpoint(endpoint) {
  const token = getAuthToken()
  if (!token) {
    console.warn(`Cannot test ${endpoint}: No token available`)
    return { success: false, status: 'No token available' }
  }
  
  try {
    console.log(`Testing endpoint: ${endpoint}`)
    // Ensure endpoint has trailing slash for Django URL patterns
    const url = endpoint.endsWith('/') ? `/api/v1/${endpoint}` : `/api/v1/${endpoint}/`
    const response = await axios.get(url, {
      headers: {
        'Authorization': `Token ${token}`
      }
    })
    
    // Check if response has data
    const hasData = response.data !== undefined && response.data !== null
    const dataType = hasData ? 
      (Array.isArray(response.data) ? 'array' : 
       (response.data.results ? 'paginated' : 'object')) : 'none'
    
    // Log data format for debugging
    console.log(`${endpoint} response type:`, dataType)
    
    return { 
      success: true, 
      status: `${response.status} OK (${dataType})`,
      data: response.data,
      dataType
    }
  } catch (error) {
    console.error(`Error testing ${endpoint}:`, error)
    return { 
      success: false, 
      status: error.response ? `${error.response.status} ${error.response.statusText}` : error.message
    }
  }
}



/**
 * Runs tests on multiple critical API endpoints
 * @returns {Promise<Array>} Test results
 */
export async function runEndpointTests() {
  const endpoints = [
    'infrastructure/containers',
    'inventory/feed-recommendations',
    'inventory/feeds',
    'batch/batches',
    'auth/users/me'
  ]
  
  const results = []
  
  // First apply the token globally
  const tokenApplied = applyTokenGlobally()
  if (!tokenApplied) {
    console.warn('No token available to apply before running tests')
    results.push({
      endpoint: 'Token Validation',
      status: 'No token available',
      success: false
    })
    return results
  }
  
  // Add token validation result
  results.push({
    endpoint: 'Token Validation',
    status: 'Token applied to requests',
    success: true
  })
  
  // Test each endpoint
  for (const endpoint of endpoints) {
    const result = await testEndpoint(endpoint)
    results.push({
      endpoint,
      status: result.status,
      success: result.success
    })
  }
  
  console.table(results)
  return results
}

/**
 * Setup auth debugging tools in the window object for console access
 */
export function setupAuthDebugger() {
  if (typeof window === 'undefined') return
  
  // First make sure default headers are set up
  setupAxiosDefaults()
  
  // Make debugging tools available on window
  window.authDebug = {
    checkToken: checkAuthToken,
    refreshToken: refreshDevToken,
    setToken: setAuthToken,
    setTestToken: setTestToken,
    clearToken: clearAuthToken,
    testEndpoint: testApiEndpoint,
  }
  
  console.log('Auth debugger initialized and available via window.authDebug')
}

// Alias for testEndpoint to maintain API compatibility
export function testApiEndpoint(endpoint) {
  return testEndpoint(endpoint)
}

export default {
  setupAuthDebugger,
  checkAuthToken,
  refreshDevToken,
  setAuthToken,
  setTestToken,
  clearAuthToken,
  testApiEndpoint,
  setupAxiosDefaults
}
