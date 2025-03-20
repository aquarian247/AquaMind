import { createRouter, createWebHistory } from 'vue-router'

// Import the route components
import LoginView from '../views/auth/LoginView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'

// Authentication guard
function requireAuth(to, from, next) {
  // Check if the user is authenticated (has a valid token)
  const token = localStorage.getItem('token')
  console.log('Auth check for route:', to.path, 'Token exists:', !!token)
  
  if (!token) {
    // User is not authenticated, redirect to login
    console.log('No token found, redirecting to login')
    return next({ name: 'login' })
  }
  
  // User is authenticated, proceed
  console.log('User authenticated, proceeding to route:', to.path)
  next()
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
    }
  ]
})

export default router
