<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const loading = ref(false)
const error = ref(null)
const user = ref(authStore.getUser)

// Simple initialization
onMounted(() => {
  console.log('Dashboard mounted')
  console.log('Current user:', authStore.getUser)
  console.log('Token in localStorage:', localStorage.getItem('token'))
})
</script>

<template>
  <AppLayout>
    <div>
      <h1 class="text-2xl font-bold mb-5">Dashboard</h1>
      
      <!-- Loading and error states -->
      <div v-if="loading" class="flex justify-center py-8">
        <div class="animate-pulse text-blue-600">Loading dashboard data...</div>
      </div>
      
      <div v-else-if="error" class="bg-red-100 border-l-4 border-red-500 p-4 mb-5">
        <p class="text-red-700">{{ error }}</p>
      </div>
      
      <!-- Dashboard content -->
      <div v-else class="mb-8">
        <div class="card bg-white p-8 rounded shadow hover:shadow-lg transition-shadow">
          <h2 class="text-xl font-bold mb-4 text-blue-800">Welcome to AquaMind!</h2>
          <p class="text-lg mb-2">
            You've successfully logged in as <span class="font-bold">{{ user?.username || 'Unknown User' }}</span>.
          </p>
          <p class="text-gray-600">
            This is a simplified dashboard to ensure authentication is working properly.
            Additional functionality will be implemented according to the project plan.
          </p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
