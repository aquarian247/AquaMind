// AquaMind Frontend Main Entry - Fixed Version
import { createApp, markRaw } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import envConfig from './utils/env-config'
import './assets/styles/main.css'
import { useAuthStore } from './store/auth'
import useApi from './composables/useApi'
import Toast from 'vue-toastification'; 
import 'vue-toastification/dist/index.css'; 

// Global error handling
console.log('%c AquaMind Vue Application ', 'background: #0056b3; color: white; font-size: 16px; padding: 5px;')
console.log('Starting application initialization...')

// Create the pinia instance
console.log('Setting up Pinia state management')
const pinia = createPinia()

// Add router to store as a property
pinia.use(({ store }) => {
  store.router = markRaw(router)
})

// Create the app instance with error handling
try {
  console.log('Creating Vue app instance')
  const app = createApp(App)
  
  // Configure error handler
  app.config.errorHandler = (error, vm, info) => {
    console.error('Vue Error:', error)
    console.error('Component:', vm?.$options?.name || 'Unknown component')
    console.error('Error Info:', info)
  }
  
  // Install plugins
  console.log('Installing Pinia plugin')
  app.use(pinia)

  console.log('Installing Toast plugin') 
  app.use(Toast); 

  // Get auth store instance
  const authStore = useAuthStore()
  console.log('Performing initial authentication check...')

  // Wrap the rest of the setup in an async function to use await
  async function initializeAndMountApp() {
    try {
      await authStore.checkAuthAndAutoLogin()
      console.log('Initial authentication check complete.')

      // Install router after auth check
      console.log('Installing Router plugin')
      app.use(router)

      // Mount the app
      console.log('Mounting app to #app element')
      app.mount('#app')
      console.log('App mounted successfully!')
    } catch (error) {
      console.error("Failed during initial auth check or app mounting:", error);
      // Optional: Display a user-friendly error message in the DOM
      document.getElementById('app').innerHTML = 
        '<div style="padding: 20px; text-align: center; color: red;">' +
        '<h2>Application Initialization Failed</h2>' +
        '<p>Could not initialize the application. Please check the console or contact support.</p>' +
        '</div>';
    }
  }

  // Execute the initialization function
  initializeAndMountApp();
} catch (e) {
  console.error('App creation/mounting error:', e)
  
  // Display user-friendly error
  document.getElementById('app').innerHTML = `
    <div style="padding: 20px; color: red; text-align: center;">
      <h2>Error Loading Application</h2>
      <p>There was a problem loading the AquaMind application. Please check the browser console for more details.</p>
      <pre style="text-align: left; background: #f7f7f7; padding: 10px; margin-top: 20px;">${e.message}</pre>
    </div>
  `
}
