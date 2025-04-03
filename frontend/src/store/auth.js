import { defineStore } from 'pinia'
import axios from 'axios'

// Create a specific instance for auth with CSRF support
const authApi = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

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

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // User info
    user: null,
    // Authentication tokens
    token: localStorage.getItem('token') || null,
    // Loading state
    loading: false,
    // Error message
    error: null,
    // For testing - hardcoded credentials
    testCredentials: {
      username: 'testuser',
      password: 'password123'
    }
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.token,
    getUser: (state) => state.user,
    getError: (state) => state.error
  },
  
  actions: {
    async login(username, password) {
      this.loading = true
      this.error = null
      
      try {
        console.log('Auth store: login attempt')
        // Use test credentials for debugging
        const credentials = {
          username: username || this.testCredentials.username,
          password: password || this.testCredentials.password
        }
        console.log('Using credentials:', credentials.username)
        
        // First, get the CSRF token by making a GET request to the Django server
        await axios.get('/api/csrf/', { withCredentials: true })
        
        // Get the CSRF token from cookies
        const csrfToken = getCsrfToken()
        
        // Call the Django token auth endpoint with CSRF token
        const response = await authApi.post('/auth/token/', credentials, {
          headers: {
            'X-CSRFToken': csrfToken
          }
        })
        
        console.log('Auth store: received response', response.data)
        
        // Store the token in localStorage and state
        const token = response.data.token
        if (!token) {
          console.error('No token received in response:', response.data)
          throw new Error('No token received from server')
        }
        
        localStorage.setItem('token', token)
        this.token = token
        
        // Set the user info directly from the response
        this.user = {
          id: response.data.user_id,
          username: response.data.username,
          email: response.data.email
        }
        
        console.log('Auth store: login successful, user:', this.user)
        return true
      } catch (error) {
        console.error('Login error:', error)
        this.error = error.response?.data?.error || error.response?.data?.detail || error.message || 'Login failed. Please check your credentials.'
        return false
      } finally {
        this.loading = false
      }
    },
    
    async fetchUserInfo() {
      if (!this.token) return
      
      try {
        // Set the authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        
        // Fetch user info from the Django API
        const response = await axios.get('/api/users/me/')
        this.user = response.data
      } catch (error) {
        // If there's an error (e.g., token expired), log out
        this.logout()
      }
    },
    
    logout() {
      // Clear the token and user info
      localStorage.removeItem('token')
      this.token = null
      this.user = null
      
      // Remove the authorization header
      delete axios.defaults.headers.common['Authorization']
    }
  }
})
