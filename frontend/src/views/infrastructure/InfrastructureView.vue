<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { useApi } from '@/composables/useApi'

const api = useApi()
const loading = ref(true)
const error = ref(null)
const stations = ref([])
const selectedStation = ref(null)
const containers = ref([])
const containerLoading = ref(false)

// Fetch stations
async function fetchStations() {
  loading.value = true
  error.value = null
  
  try {
    const response = await api.get('/infrastructure/freshwater-stations/')
    stations.value = response.results || response
  } catch (err) {
    error.value = 'Failed to load stations'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Fetch containers for a station
async function fetchContainersForStation(stationId) {
  if (!stationId) return
  
  containerLoading.value = true
  selectedStation.value = stations.value.find(s => s.id === stationId)
  
  try {
    const response = await api.get('/infrastructure/containers/', { station: stationId })
    containers.value = response.results || response
  } catch (err) {
    console.error('Failed to load containers:', err)
    containers.value = []
  } finally {
    containerLoading.value = false
  }
}

// Handle station selection
function selectStation(stationId) {
  fetchContainersForStation(stationId)
}

onMounted(() => {
  fetchStations()
})
</script>

<template>
  <AppLayout>
    <div>
      <h1 class="text-2xl font-bold mb-5">Infrastructure Management</h1>
      
      <!-- Loading and error states -->
      <div v-if="loading" class="flex justify-center py-8">
        <div class="animate-pulse text-blue-600">Loading infrastructure data...</div>
      </div>
      
      <div v-else-if="error" class="bg-red-100 border-l-4 border-red-500 p-4 mb-5">
        <p class="text-red-700">{{ error }}</p>
      </div>
      
      <!-- Infrastructure content -->
      <div v-else class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <!-- Stations list -->
        <div class="md:col-span-1">
          <h2 class="text-lg font-semibold mb-3">Freshwater Stations</h2>
          <div class="bg-white shadow rounded-lg">
            <ul class="divide-y divide-gray-200">
              <li v-if="stations.length === 0" class="p-4 text-gray-500">
                No stations found
              </li>
              <li 
                v-for="station in stations" 
                :key="station.id" 
                @click="selectStation(station.id)"
                class="p-4 hover:bg-blue-50 cursor-pointer transition-colors"
                :class="{ 'bg-blue-50': selectedStation && selectedStation.id === station.id }"
              >
                <div class="font-medium">{{ station.name }}</div>
                <div class="text-sm text-gray-500">{{ station.area ? station.area.name : 'No area' }}</div>
              </li>
            </ul>
          </div>
        </div>
        
        <!-- Container details -->
        <div class="md:col-span-3">
          <div v-if="selectedStation" class="mb-4">
            <h2 class="text-lg font-semibold mb-3">{{ selectedStation.name }} Containers</h2>
            
            <!-- Container loading indicator -->
            <div v-if="containerLoading" class="flex justify-center py-8">
              <div class="animate-pulse text-blue-600">Loading containers...</div>
            </div>
            
            <!-- Container list -->
            <div v-else-if="containers.length > 0" class="bg-white shadow rounded-lg overflow-hidden">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Capacity</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="container in containers" :key="container.id">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="font-medium text-gray-900">{{ container.name }}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div>{{ container.container_type ? container.container_type.name : 'Unknown' }}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div>{{ container.max_capacity_kg }} kg</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        Active
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <!-- Empty container state -->
            <div v-else class="bg-white shadow rounded-lg p-6 text-center text-gray-500">
              No containers found for this station.
            </div>
          </div>
          
          <!-- No station selected state -->
          <div v-else class="bg-white shadow rounded-lg p-6 text-center text-gray-500">
            Select a station to view its containers.
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
