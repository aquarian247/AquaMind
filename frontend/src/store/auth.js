import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // User info
    user: null,
    // Authentication tokens
    token: localStorage.getItem('token') || null,
    // Loading state
    loading: false,
    // Error message
    error: null
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
        // Call the Django token auth endpoint
        const response = await axios.post('/api/auth/token/', {
          username,
          password
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
