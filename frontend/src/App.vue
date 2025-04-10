<script setup>
import { onMounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useAuthStore } from './store/auth'
import authDebugger from './utils/auth-debugger'

// Extract functions from the module
const { 
  setupAuthDebugger, 
  refreshDevToken, 
  checkAuthToken, 
  testApiEndpoint, 
  setupAxiosDefaults 
} = authDebugger
import axios from 'axios'
import envConfig from './utils/env-config'

const authStore = useAuthStore()
const router = useRouter()
// Use the environment configuration
const isDevMode = envConfig.isDev
const isAuthenticating = ref(true)
const manuallyAuthenticating = ref(false)

// Initialize auth debugging and setup axios defaults for token
setupAuthDebugger()
setupAxiosDefaults()

// Register axios instance for global token management
if (typeof window !== 'undefined' && !window.__axiosInstances) {
  window.__axiosInstances = []
}
if (typeof window !== 'undefined') {
  window.__axiosInstances.push(axios)
}

// Only in development mode, check authentication and test API endpoints
onMounted(async () => {
  console.log('App mounted, checking authentication')
  
  // Check if we're already on the login page
  if (router.currentRoute.value.name === 'login') {
    isAuthenticating.value = false
    return
  }
  
  try {
    // First check if we have a valid token already
    const existingToken = checkAuthToken()
    let isAuthenticated = !!existingToken
    
    // If not authenticated and in development mode, try auto-login
    if (!isAuthenticated && isDevMode) {
      console.log('Not authenticated in dev mode, attempting auto-login')
      // First try the auth store method
      isAuthenticated = await authStore.checkAuthAndAutoLogin()
      
      // If that fails, try the direct approach as a fallback
      if (!isAuthenticated) {
        console.log('Store authentication failed, trying direct dev-auth endpoint')
        const token = await refreshDevToken()
        isAuthenticated = !!token
      }
    }
    
    // If still not authenticated, redirect to login
    if (!isAuthenticated) {
      console.log('No authentication token found, redirecting to login')
      
      // In development, we'll just show the auth UI instead of redirecting
      if (isDevMode) {
        isAuthenticating.value = false
        return
      }
      
      router.push('/login')
    } else {
      console.log('Authentication successful')
      
      // In dev mode, run diagnostics on the API endpoints
      if (isDevMode) {
        console.log('Running API endpoint diagnostics...')
        // First ensure the token is properly applied to axios defaults
        setupAxiosDefaults()
        
        // Allow a moment for token to be properly set
        setTimeout(async () => {
          // Test critical endpoints with explicit auth headers
          console.log('Testing infrastructure/containers endpoint...')
          await testApiEndpoint('infrastructure/containers/')
          
          // Test feed-recommendations endpoint with explicit auth headers
          console.log('Testing feed-recommendations endpoint...')
          await testApiEndpoint('inventory/feed-recommendations/')
          
          // Test batch endpoint
          console.log('Testing batches endpoint...')
          await testApiEndpoint('batch/batches/')
        }, 1000)
      }
      
      // If we were trying to access a specific route before being redirected to login,
      // we can restore that route here
      const redirectPath = sessionStorage.getItem('redirectPath')
      if (redirectPath && redirectPath !== '/login') {
        console.log('Restoring previous route:', redirectPath)
        sessionStorage.removeItem('redirectPath')
        router.push(redirectPath)
      }
    }
  } catch (error) {
    console.error('Authentication error:', error)
    if (!isDevMode) {
      router.push('/login')
    }
  } finally {
    isAuthenticating.value = false
  }
})
</script>

<template>
  <div class="app-container">
    <!-- Development mode indicator with enhanced authentication tools -->
    <div v-if="isDevMode" class="dev-mode-indicator">
      <span>DEV MODE</span>
      <button 
        v-if="!authStore.isAuthenticated" 
        @click="manuallyAuthenticating = true; refreshDevToken().then(token => {
          if (token) location.reload();
          manuallyAuthenticating = false;
        })"
        :disabled="manuallyAuthenticating"
      >
        {{ manuallyAuthenticating ? 'Authenticating...' : 'Auto Login' }}
      </button>
    </div>
    
    <!-- Loading state while authenticating -->
    <div v-if="isAuthenticating" class="auth-loading">
      <div class="spinner"></div>
      <p>Authenticating...</p>
    </div>
    
    <!-- Main app content -->
    <RouterView v-else />
  </div>
</template>

<style>
.app-container {
  min-height: 100vh;
  position: relative;
}

.dev-mode-indicator {
  position: fixed;
  top: 0;
  right: 0;
  background-color: rgba(255, 152, 0, 0.8);
  color: #333;
  font-size: 0.75rem;
  padding: 4px 8px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dev-mode-indicator button {
  background-color: #333;
  color: white;
  border: none;
  border-radius: 2px;
  padding: 2px 6px;
  font-size: 0.75rem;
  cursor: pointer;
}

.auth-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #0056b3;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
