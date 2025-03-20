import axios from 'axios'

// Create a custom axios instance
const api = axios.create({
  baseURL: '/api/v1', // Base URL for API requests
  timeout: 10000, // Request timeout in milliseconds
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Request interceptor for API calls
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Token ${token}`
    }
    console.log(`Sending ${config.method?.toUpperCase()} request to ${config.url}`, { headers: config.headers, params: config.params })
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
    console.log(`Response from ${response.config.url}:`, { status: response.status, data: response.data })
    return response
  },
  async (error) => {
    console.error(`API Error: ${error.config?.url}`, {
      status: error.response?.status,
      message: error.message,
      response: error.response?.data
    })
    
    const originalRequest = error.config
    
    // Handle token refresh or redirect to login on auth errors
    if (error.response?.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true
      
      // You could implement token refresh logic here
      // For now, just redirect to login
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export function useApi() {
  return {
    // GET request
    async get(url, params = {}) {
      try {
        const response = await api.get(url, { params })
        return response.data
      } catch (error) {
        console.error(`GET ${url} error:`, error)
        throw error
      }
    },
    
    // POST request
    async post(url, data = {}) {
      try {
        const response = await api.post(url, data)
        return response.data
      } catch (error) {
        console.error(`POST ${url} error:`, error)
        throw error
      }
    },
    
    // PUT request
    async put(url, data = {}) {
      try {
        const response = await api.put(url, data)
        return response.data
      } catch (error) {
        console.error(`PUT ${url} error:`, error)
        throw error
      }
    },
    
    // PATCH request
    async patch(url, data = {}) {
      try {
        const response = await api.patch(url, data)
        return response.data
      } catch (error) {
        console.error(`PATCH ${url} error:`, error)
        throw error
      }
    },
    
    // DELETE request
    async delete(url) {
      try {
        const response = await api.delete(url)
        return response.data
      } catch (error) {
        console.error(`DELETE ${url} error:`, error)
        throw error
      }
    }
  }
}
