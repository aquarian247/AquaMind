<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const authStore = useAuthStore()

// Pre-fill with test credentials for development
const username = ref('testuser')
const password = ref('password123')
const errorMessage = ref('')
const isLoading = ref(false)

// Login function
async function handleLogin() {
  if (!username.value || !password.value) {
    errorMessage.value = 'Please enter both username and password'
    return
  }

  isLoading.value = true
  console.log('Attempting login with:', username.value)
  const success = await authStore.login(username.value, password.value)
  console.log('Login result:', success, 'token:', localStorage.getItem('token'))
  isLoading.value = false

  if (success) {
    console.log('Login successful, redirecting to dashboard')
    router.push('/dashboard')
  } else {
    console.log('Login failed:', authStore.getError)
    errorMessage.value = authStore.getError || 'Login failed'
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-blue-50">
    <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-blue-800">AquaMind</h1>
        <p class="mt-2 text-gray-600">Aquaculture Management System</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="mt-8 space-y-6">
        <div v-if="errorMessage" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <span class="block sm:inline">{{ errorMessage }}</span>
        </div>
        
        <div>
          <label for="username" class="form-label">Username</label>
          <input 
            id="username" 
            v-model="username" 
            name="username" 
            type="text" 
            required 
            class="form-input" 
            placeholder="Username"
          />
        </div>
        
        <div>
          <label for="password" class="form-label">Password</label>
          <input 
            id="password" 
            v-model="password" 
            name="password" 
            type="password" 
            required 
            class="form-input" 
            placeholder="Password"
          />
        </div>
        
        <div>
          <button 
            type="submit" 
            class="w-full btn-primary" 
            :disabled="isLoading"
          >
            {{ isLoading ? 'Logging in...' : 'Log in' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
