import axios from 'axios'
import { setupCSRF, fetchCSRFToken } from '@/utils/csrf'
import { ref } from 'vue'
import { createAuthenticatedAxios, applyTokenGlobally } from '@/utils/api-auth'

// Create an authenticated API instance with consistent token handling
const api = createAuthenticatedAxios()

// Enable CSRF token handling
api.defaults.withCredentials = true // Important for sending cookies

// Log that the API module has been loaded (useful for debugging)
console.log('API module initialized with baseURL:', api.defaults.baseURL)

// Set up CSRF token handling
setupCSRF(api)

// Fetch a CSRF token immediately on application load
fetchCSRFToken()

// Apply token to all axios instances for global consistency
applyTokenGlobally()

// Function to get CSRF token from cookies
function getCsrfToken() {
  const name = 'csrftoken='
  const decodedCookie = decodeURIComponent(document.cookie)
  const cookieArray = decodedCookie.split(';')
  
  for (let i = 0; i < cookieArray.length; i++) {
    let cookie = cookieArray[i].trim()
    if (cookie.indexOf(name) === 0) {
      return cookie.substring(name.length, cookie.length)
    }
  }
  return ''
}

// Request interceptor for API calls with enhanced logging
api.interceptors.request.use(
  (config) => {
    try {
      // Get authentication token from localStorage - already handled by createAuthenticatedAxios
      // but we'll log it for debugging purposes
      const token = localStorage.getItem('token')
      const tokenFragment = token ? `${token.substring(0, 6)}...${token.substring(token.length - 6)}` : 'None'
      console.log(`API Request to: ${config.url}`, { 
        hasToken: !!token,
        tokenFragment: token ? tokenFragment : null,
        authHeader: config.headers['Authorization'] ? 'Present' : 'Missing'
      })
    } catch (error) {
      console.error('Error in request interceptor:', error)
    }
    
    // Ensure trailing slash for Django URL patterns
    // Django typically expects trailing slashes in URLs
    if (!config.url.endsWith('/') && !config.url.includes('?')) {
      config.url = `${config.url}/`
    }
    
    // Log the full request details
    console.log('Making API request:', {
      method: config.method,
      url: config.url,
      headers: config.headers,
      params: config.params,
      hasData: !!config.data
    })
    
    return config
  },
  (error) => {
    console.error('Request interceptor error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for API calls
api.interceptors.response.use(
  (response) => {
    // Log the full response details
    console.log(`API Response from ${response.config.url}:`, {
      status: response.status,
      statusText: response.statusText,
      dataReceived: !!response.data
    })
    
    return response
  },
  async (error) => {
    // Log all error details for debugging
    console.error(`API Error: ${error.config?.url}`, {
      status: error.response?.status,
      message: error.message
    })
    
    if (error.response?.data) {
      console.error('Error response data:', error.response.data)
    }
    
    const originalRequest = error.config
    
    // Handle authentication errors with enhanced recovery logic
    if (error.response?.status === 401 && !originalRequest?._retry) {
      console.warn('Authentication error detected, trying to recover...')
      originalRequest._retry = true
      
      // In development mode, try auto-authentication
      const isDevelopmentMode = true; // Always enable during development
      if (isDevelopmentMode) {
        try {
          // Try to get a new token from dev-auth endpoint
          console.log('Attempting dev mode auto-authentication recovery')
          const response = await axios.get('/api/v1/auth/dev-auth/')
          if (response.data.token) {
            // Set the new token
            localStorage.setItem('token', response.data.token)
            // Apply token globally to ensure consistency
            applyTokenGlobally()
            // Update the original request with the new token
            originalRequest.headers['Authorization'] = `Token ${response.data.token}`
            console.log('Auto-recovered with dev token, retrying request')
            // Use axios directly for the retry to ensure headers are fresh
            return axios(originalRequest)
          }
        } catch (authError) {
          console.error('Auto-recovery attempt failed:', authError)
        }
      }
      
      // If auto-recovery failed or not in dev mode, redirect to login
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

// Composable function to provide access to the API instance
export function useApi() {
  const isLoading = ref(false)
  const error = ref(null)
  
  /**
   * Make a GET request to the specified endpoint
   * @param {string} endpoint - API endpoint to call (without the /api/v1/ prefix)
   * @param {Object} params - Optional query parameters
   * @returns {Promise<any>} - Response data
   */
  const get = async (endpoint, params = {}) => {
    isLoading.value = true
    error.value = null
    
    try {
      // Always add a timestamp to prevent caching (helpful for development)
      const isDevelopmentMode = true; // Always enable during development
      if (isDevelopmentMode) {
        params._t = new Date().getTime()
      }
      
      console.log(`Making GET request to ${endpoint} with params:`, params)
      const response = await api.get(endpoint, { params })
      console.log(`GET ${endpoint} response:`, response.data)
      return response.data
    } catch (err) {
      console.error(`GET ${endpoint} failed:`, err)
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Make a POST request to the specified endpoint
   * @param {string} endpoint - API endpoint to call (without the /api/v1/ prefix)
   * @param {Object} data - Request payload
   * @returns {Promise<any>} - Response data
   */
  const post = async (endpoint, data = {}) => {
    isLoading.value = true
    error.value = null
    
    try {
      console.log(`Making POST request to ${endpoint} with data:`, data)
      const response = await api.post(endpoint, data)
      console.log(`POST ${endpoint} response:`, response.data)
      return response.data
    } catch (err) {
      console.error(`POST ${endpoint} failed:`, err)
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Make a PUT request to the specified endpoint
   * @param {string} endpoint - API endpoint to call (without the /api/v1/ prefix)
   * @param {Object} data - Request payload
   * @returns {Promise<any>} - Response data
   */
  const put = async (endpoint, data = {}) => {
    isLoading.value = true
    error.value = null
    
    try {
      console.log(`Making PUT request to ${endpoint} with data:`, data)
      const response = await api.put(endpoint, data)
      console.log(`PUT ${endpoint} response:`, response.data)
      return response.data
    } catch (err) {
      console.error(`PUT ${endpoint} failed:`, err)
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Make a PATCH request to the specified endpoint
   * @param {string} endpoint - API endpoint to call (without the /api/v1/ prefix)
   * @param {Object} data - Request payload
   * @returns {Promise<any>} - Response data
   */
  const patch = async (endpoint, data = {}) => {
    isLoading.value = true
    error.value = null
    
    try {
      console.log(`Making PATCH request to ${endpoint} with data:`, data)
      const response = await api.patch(endpoint, data)
      console.log(`PATCH ${endpoint} response:`, response.data)
      return response.data
    } catch (err) {
      console.error(`PATCH ${endpoint} failed:`, err)
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Make a DELETE request to the specified endpoint
   * @param {string} endpoint - API endpoint to call (without the /api/v1/ prefix)
   * @returns {Promise<any>} - Response data
   */
  const deleteRequest = async (endpoint) => {
    isLoading.value = true
    error.value = null
    
    try {
      console.log(`Making DELETE request to ${endpoint}`)
      const response = await api.delete(endpoint)
      console.log(`DELETE ${endpoint} response:`, response.data)
      return response.data
    } catch (err) {
      console.error(`DELETE ${endpoint} failed:`, err)
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  return {
    get,
    post,
    put,
    patch,
    delete: deleteRequest,
    isLoading,
    error
  }
}

export default { useApi }
