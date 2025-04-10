<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.getUser)

// Navigation items
const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: 'chart-pie' },
  { name: 'Infrastructure', path: '/infrastructure', icon: 'building' },
  { name: 'Batch', path: '/batch', icon: 'fish' },
  { name: 'Inventory', path: '/inventory', icon: 'box' },
  // { name: 'Environmental', path: '/environmental', icon: 'thermometer' } // Removed non-existent route
]

// Logout function
function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Sidebar -->
    <div class="fixed inset-y-0 left-0 w-64 bg-blue-800 text-white shadow-lg">
      <div class="flex items-center justify-center h-16 border-b border-blue-700">
        <h1 class="text-xl font-bold">AquaMind</h1>
      </div>
      <nav class="mt-5">
        <ul>
          <li v-for="item in navItems" :key="item.name" class="mb-1">
            <router-link :to="item.path" class="flex items-center px-4 py-3 hover:bg-blue-700" active-class="bg-blue-700">
              <span class="ml-2">{{ item.name }}</span>
            </router-link>
          </li>
        </ul>
      </nav>
    </div>

    <!-- Main content -->
    <div class="ml-64">
      <!-- Top navigation -->
      <div class="bg-white h-16 flex items-center justify-between px-4 shadow-sm">
        <h2 class="text-lg font-semibold text-gray-800">{{ $route.name }}</h2>
        <div class="flex items-center">
          <span v-if="user" class="mr-4">{{ user.username }}</span>
          <button @click="logout" class="btn-secondary text-sm">Logout</button>
        </div>
      </div>

      <!-- Page content -->
      <div class="p-6">
        <slot />
      </div>
    </div>
  </div>
</template>
