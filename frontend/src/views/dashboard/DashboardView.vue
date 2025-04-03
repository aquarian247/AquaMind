<script setup>
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { useAuthStore } from '@/store/auth'
import { useApi } from '@/composables/useApi'

const authStore = useAuthStore()
const api = useApi()
const loading = ref(true)
const error = ref(null)
const user = ref(authStore.getUser)

// Dashboard data
const environmentalReadings = ref([])
const batches = ref([])
const activeBatches = computed(() => batches.value.filter(batch => batch.status === 'ACTIVE'))
const recentWeatherData = ref([])
const totalBiomass = computed(() => {
  return batches.value.reduce((total, batch) => total + (parseFloat(batch.biomass_kg) || 0), 0)
})
const totalPopulation = computed(() => {
  return batches.value.reduce((total, batch) => total + (parseInt(batch.population_count) || 0), 0)
})

// Fetch dashboard data
async function fetchDashboardData() {
  loading.value = true
  error.value = null
  
  try {
    console.log('Starting to fetch dashboard data...')
    
    try {
      // Fetch recent environmental readings
      console.log('Fetching environmental readings...')
      const envResponse = await api.get('/environmental/readings/recent/')
      console.log('Environmental readings response:', envResponse)
      // DRF action methods return data directly, not wrapped in results
      environmentalReadings.value = Array.isArray(envResponse) ? envResponse : []
    } catch (envErr) {
      console.error('Error fetching environmental readings:', envErr)
      // Continue with other requests even if this one fails
    }
    
    try {
      // Fetch active batches
      console.log('Fetching active batches...')
      const batchesResponse = await api.get('/batch/batches/', { params: { status: 'ACTIVE' } })
      console.log('Batches response:', batchesResponse)
      // Standard viewset list endpoints return data in results property
      batches.value = batchesResponse.results || (Array.isArray(batchesResponse) ? batchesResponse : [])
    } catch (batchErr) {
      console.error('Error fetching batches:', batchErr)
      // Continue with other requests even if this one fails
    }
    
    try {
      // Fetch recent weather data
      console.log('Fetching weather data...')
      const weatherResponse = await api.get('/environmental/weather/recent/')
      console.log('Weather response:', weatherResponse)
      // DRF action methods return data directly, not wrapped in results
      recentWeatherData.value = Array.isArray(weatherResponse) ? weatherResponse : []
    } catch (weatherErr) {
      console.error('Error fetching weather data:', weatherErr)
      // Continue with other requests even if this one fails
    }
    
    console.log('Dashboard data loaded:', { 
      readings: environmentalReadings.value.length,
      batches: batches.value.length,
      weather: recentWeatherData.value.length
    })
    
    // If all requests failed, throw an error to trigger the catch block
    if (environmentalReadings.value.length === 0 && 
        batches.value.length === 0 && 
        recentWeatherData.value.length === 0) {
      throw new Error('No data could be loaded for the dashboard')
    }
    
  } catch (err) {
    error.value = `Failed to load dashboard data: ${err.message || 'Unknown error'}`
    console.error('Dashboard data error:', err)
  } finally {
    loading.value = false
  }
}

// Format temperature for display
function formatTemperature(value) {
  return value ? `${parseFloat(value).toFixed(1)}°C` : 'N/A'
}

// Format date for display
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

onMounted(() => {
  fetchDashboardData()
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
      <div v-else>
        <!-- Summary cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <!-- Total Biomass -->
          <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Total Biomass</h3>
            <p class="text-3xl font-bold text-blue-600">{{ totalBiomass.toFixed(2) }} kg</p>
            <p class="text-sm text-gray-500 mt-1">Across {{ activeBatches.length }} active batches</p>
          </div>
          
          <!-- Total Population -->
          <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Total Population</h3>
            <p class="text-3xl font-bold text-green-600">{{ totalPopulation.toLocaleString() }}</p>
            <p class="text-sm text-gray-500 mt-1">Fish in active batches</p>
          </div>
          
          <!-- Environmental Status -->
          <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-semibold text-gray-700 mb-2">Environmental Status</h3>
            <p class="text-xl font-medium text-gray-800">
              <span v-if="environmentalReadings.length > 0" class="text-green-600">●</span>
              <span v-else class="text-yellow-500">●</span>
              {{ environmentalReadings.length > 0 ? 'Normal' : 'No recent data' }}
            </p>
            <p class="text-sm text-gray-500 mt-1">{{ environmentalReadings.length }} sensor readings in last 24h</p>
          </div>
        </div>
        
        <!-- Environmental readings section -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold mb-4">Recent Environmental Readings</h2>
          <div v-if="environmentalReadings.length === 0" class="bg-white p-6 rounded-lg shadow text-center text-gray-500">
            No recent environmental readings available
          </div>
          <div v-else class="bg-white rounded-lg shadow overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Parameter</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Container</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="reading in environmentalReadings.slice(0, 5)" :key="reading.id">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="font-medium text-gray-900">{{ reading.parameter?.name || 'Unknown' }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div>{{ reading.container?.name || 'N/A' }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="font-medium">
                      {{ reading.value }} {{ reading.parameter?.unit || '' }}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ new Date(reading.reading_time).toLocaleString() }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Active batches section -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold mb-4">Active Batches</h2>
          <div v-if="activeBatches.length === 0" class="bg-white p-6 rounded-lg shadow text-center text-gray-500">
            No active batches available
          </div>
          <div v-else class="bg-white rounded-lg shadow overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Batch #</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Species</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Population</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Biomass</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="batch in activeBatches" :key="batch.id">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="font-medium text-gray-900">{{ batch.batch_number }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div>{{ batch.species_name || 'Unknown' }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div>{{ batch.lifecycle_stage_name || 'Unknown' }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div>{{ batch.population_count?.toLocaleString() || '0' }}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div>{{ parseFloat(batch.biomass_kg || 0).toFixed(2) }} kg</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDate(batch.start_date) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Weather data section -->
        <div class="mb-8" v-if="recentWeatherData.length > 0">
          <h2 class="text-xl font-semibold mb-4">Weather Conditions</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div v-for="weather in recentWeatherData" :key="weather.id" class="bg-white p-6 rounded-lg shadow">
              <h3 class="font-semibold text-lg mb-2">{{ weather.area?.name || 'Unknown Area' }}</h3>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <p class="text-sm text-gray-500">Temperature</p>
                  <p class="text-xl font-medium">{{ formatTemperature(weather.temperature) }}</p>
                </div>
                <div>
                  <p class="text-sm text-gray-500">Humidity</p>
                  <p class="text-xl font-medium">{{ weather.humidity ? `${weather.humidity}%` : 'N/A' }}</p>
                </div>
                <div>
                  <p class="text-sm text-gray-500">Wind Speed</p>
                  <p class="text-xl font-medium">{{ weather.wind_speed ? `${weather.wind_speed} m/s` : 'N/A' }}</p>
                </div>
                <div>
                  <p class="text-sm text-gray-500">Updated</p>
                  <p class="text-sm">{{ new Date(weather.timestamp).toLocaleString() }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
