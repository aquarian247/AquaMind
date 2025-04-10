import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

// Import the route components
import LoginView from '../views/auth/LoginView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'

// Authentication guard
function requireAuth(to, from, next) {
  const authStore = useAuthStore()
  
  // Auth check is guaranteed to be complete by the time the guard runs (due to main.js change)
  console.log('Router Guard: Checking authentication status.');
  
  if (!authStore.isAuthenticated) {
    // User is not authenticated, redirect to login
    console.log('Router Guard: Not authenticated, redirecting to login')
    // Pass the intended route as a query param for redirecting back after login
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else {
    // User is authenticated, proceed
    console.log('Router Guard: Authenticated, proceeding to route:', to.path)
    next()
  }
}

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      beforeEnter: requireAuth
    },
    {
      path: '/infrastructure',
      name: 'infrastructure',
      component: () => import('../views/infrastructure/InfrastructureView.vue'),
      beforeEnter: requireAuth
    },
    {
      path: '/batch',
      name: 'batch',
      component: () => import('../views/batch/BatchView.vue'),
      beforeEnter: requireAuth
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: () => import('../views/inventory/InventoryView.vue'),
      beforeEnter: requireAuth
    }
  ]
})

export default router
