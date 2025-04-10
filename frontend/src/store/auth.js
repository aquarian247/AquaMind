import { defineStore } from 'pinia'
import axios from 'axios'
import envConfig from '../utils/env-config'

/**
 * Determines if the app is running in development mode
 * Uses our centralized environment configuration
 */
// Access the direct value for consistency
const isDevelopment = envConfig.isDevelopment

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
  
  for (let i = 0; i <cookieArray.length; i++) {
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
    // Flag to indicate if the initial auth check (including dev auto-login) is complete
    authCheckComplete: false,
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
    /**
     * Auto-authenticates in development environments using the dev-auth endpoint
     * This provides a seamless development experience without manual token management
     * @returns {Promise<boolean>} Whether authentication was successful
     */
    async autoAuthenticateInDev() {
      // Only run in development mode and when not already authenticated
      if (!isDevelopment) {
        console.log('Not in development mode, skipping auto-auth')
        return false
      }
      
      // If we already have a token, check if it's still valid
      if (this.token) {
        console.log('Already have a token, checking if valid')
        // We could make a validation call here if needed
        return true
      }
      
      console.log('Auth store: attempting auto-authentication for development')
      this.loading = true
      this.error = null
      
      try {
        // Call the development-only auth endpoint
        console.log('Calling dev-auth endpoint at correct URL path')
        const response = await axios.get('/api/v1/auth/dev-auth/')
        console.log('Dev-auth response:', response.data)
        
        // Store the token and user info
        const token = response.data.token
        if (!token) {
          console.warn('Dev auth: No token received')
          return false
        }
        
        // Set the token in localStorage AND state
        console.log('Setting token in localStorage and state:', token.substring(0, 5) + '...')
        localStorage.setItem('token', token)
        this.token = token
        
        // Also set it in the default headers for axios
        axios.defaults.headers.common['Authorization'] = `Token ${token}`
        
        // Set the user info directly from the response
        this.user = {
          id: response.data.user_id,
          username: response.data.username,
          email: response.data.email || ''
        }
        
        console.log('Dev auth: Successfully authenticated as', this.user.username)
        return true
      } catch (error) {
        console.error('Dev auth failed:', error)
        if (error.response) {
          console.error('Response data:', error.response.data)
          console.error('Response status:', error.response.status)
        }
        return false
      } finally {
        this.loading = false
      }
    },
    /**
     * Authenticates a user with username and password
     * @param {string} username - User's username
     * @param {string} password - User's password 
     * @returns {Promise<boolean>} Whether login was successful
     */
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
    
    /**
     * Fetches the current user's information
     * @returns {Promise<void>}
     */
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
    
    /**
     * Logs out the current user
     */
    logout() {
      // Clear the token and user info
      localStorage.removeItem('token')
      this.token = null
      this.user = null
      
      // Remove the authorization header
      delete axios.defaults.headers.common['Authorization']
    },
    
    /**
     * Checks if user is authenticated and attempts auto-login in development if not
     * This should be called when the application starts
     * @returns {Promise<boolean>} Whether the user is authenticated
     */
    async checkAuthAndAutoLogin() {
      // Reset flag on each check
      this.authCheckComplete = false;
      let isAuthenticated = false;
      try {
        if (this.token) {
          console.log('AuthStore: Token found, assuming valid for now.');
          // TODO: Optionally add a real token validation API call here
          // If validation fails, clear the token:
          // if (!await this.validateToken()) { 
          //   this.logout(); // Use logout action to clear state
          // }
          isAuthenticated = !!this.token; // Re-check token in case validation cleared it
        } else if (isDevelopment) {
          console.log('AuthStore: No token, attempting dev auto-login...');
          isAuthenticated = await this.autoAuthenticateInDev();
        } else {
          console.log('AuthStore: No token, not in dev.');
          isAuthenticated = false;
        }
        console.log(`AuthStore: Final auth status after check: ${isAuthenticated}`);
        return isAuthenticated;
      } catch (error) {
        console.error('AuthStore: Error during auth check/auto-login:', error);
        this.logout(); // Ensure clean state on error
        isAuthenticated = false;
        return false;
      } finally {
        console.log('AuthStore: Setting authCheckComplete to true.');
        this.authCheckComplete = true; // Ensure this runs in all paths
      }
    }
  }
})
