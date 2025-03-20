<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import BatchTimeline from '@/components/batch/BatchTimeline.vue'
import { useApi } from '@/composables/useApi'

const api = useApi()
const loading = ref(true)
const error = ref(null)
const batches = ref([])
const selectedBatch = ref(null)
const batchDetails = ref(null)
const detailsLoading = ref(false)
const activeTab = ref('details') // 'details' or 'timeline'

// Status class mapping
const statusClasses = {
  'ACTIVE': 'bg-green-100 text-green-800',
  'COMPLETED': 'bg-blue-100 text-blue-800',
  'TERMINATED': 'bg-gray-100 text-gray-800'
}

// Fetch all batches
async function fetchBatches() {
  loading.value = true
  error.value = null
  
  try {
    const response = await api.get('/batch/batches/')
    batches.value = response.results || response
  } catch (err) {
    error.value = 'Failed to load batches'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Fetch details for a specific batch
async function fetchBatchDetails(batchId) {
  if (!batchId) return
  
  detailsLoading.value = true
  selectedBatch.value = batches.value.find(b => b.id === batchId)
  
  try {
    // Fetch batch details including the container assignments
    const response = await api.get(`/batch/batches/${batchId}/`)
    batchDetails.value = response
    
    // Fetch additional batch data like container assignments and growth samples
    const [assignmentsResponse, growthResponse] = await Promise.all([
      api.get(`/batch/container-assignments/`, { batch: batchId }),
      api.get(`/batch/growth-samples/`, { batch: batchId })
    ])
    
    batchDetails.value.container_assignments = assignmentsResponse.results || assignmentsResponse
    batchDetails.value.growth_samples = growthResponse.results || growthResponse
  } catch (err) {
    console.error('Failed to load batch details:', err)
    batchDetails.value = null
  } finally {
    detailsLoading.value = false
  }
}

// Handle batch selection
function selectBatch(batchId) {
  fetchBatchDetails(batchId)
}

// Switch between tabs
function setActiveTab(tab) {
  activeTab.value = tab
}

// Format date for display
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

onMounted(() => {
  fetchBatches()
})
</script>

<template>
  <AppLayout>
    <div>
      <h1 class="text-2xl font-bold mb-5">Batch Management</h1>
      
      <!-- Loading and error states -->
      <div v-if="loading" class="flex justify-center py-8">
        <div class="animate-pulse text-blue-600">Loading batch data...</div>
      </div>
      
      <div v-else-if="error" class="bg-red-100 border-l-4 border-red-500 p-4 mb-5">
        <p class="text-red-700">{{ error }}</p>
      </div>
      
      <!-- Batch content -->
      <div v-else class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <!-- Batch list -->
        <div class="md:col-span-1">
          <div class="flex justify-between items-center mb-3">
            <h2 class="text-lg font-semibold">Batches</h2>
            <button class="btn-primary text-sm">New Batch</button>
          </div>
          
          <div class="bg-white shadow rounded-lg">
            <ul class="divide-y divide-gray-200">
              <li v-if="batches.length === 0" class="p-4 text-gray-500">
                No batches found
              </li>
              <li 
                v-for="batch in batches" 
                :key="batch.id" 
                @click="selectBatch(batch.id)"
                class="p-4 hover:bg-blue-50 cursor-pointer transition-colors"
                :class="{ 'bg-blue-50': selectedBatch && selectedBatch.id === batch.id }"
              >
                <div class="font-medium">{{ batch.batch_number }}</div>
                <div class="flex items-center mt-1">
                  <span 
                    class="px-2 py-0.5 text-xs leading-5 font-medium rounded-full" 
                    :class="statusClasses[batch.status] || 'bg-gray-100'"
                  >
                    {{ batch.status }}
                  </span>
                  <span class="ml-2 text-sm text-gray-500">
                    {{ batch.species ? batch.species.name : 'Unknown species' }}
                  </span>
                </div>
              </li>
            </ul>
          </div>
        </div>
        
        <!-- Batch details -->
        <div class="md:col-span-3">
          <div v-if="selectedBatch" class="mb-4">
            <div class="flex justify-between items-center mb-3">
              <h2 class="text-lg font-semibold">Batch: {{ selectedBatch.batch_number }}</h2>
              
              <!-- Tab navigation -->
              <div class="flex space-x-1 bg-gray-100 p-1 rounded-lg">
                <button 
                  @click="setActiveTab('details')"
                  class="px-3 py-1 text-sm rounded-md focus:outline-none"
                  :class="activeTab === 'details' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'"
                >
                  Details
                </button>
                <button 
                  @click="setActiveTab('timeline')"
                  class="px-3 py-1 text-sm rounded-md focus:outline-none"
                  :class="activeTab === 'timeline' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'"
                >
                  Timeline
                </button>
              </div>
            </div>
            
            <!-- Batch details loading indicator -->
            <div v-if="detailsLoading" class="flex justify-center py-8">
              <div class="animate-pulse text-blue-600">Loading batch details...</div>
            </div>
            
            <!-- Batch details content -->
            <div v-else-if="batchDetails && activeTab === 'details'" class="space-y-6">
              <!-- Basic information card -->
              <div class="bg-white shadow rounded-lg overflow-hidden">
                <div class="px-4 py-5 sm:p-6">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Batch Number</h3>
                      <p class="mt-1 text-lg font-semibold">{{ batchDetails.batch_number }}</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Status</h3>
                      <p class="mt-1">
                        <span 
                          class="px-2 py-0.5 text-xs leading-5 font-medium rounded-full" 
                          :class="statusClasses[batchDetails.status] || 'bg-gray-100'"
                        >
                          {{ batchDetails.status }}
                        </span>
                      </p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Species</h3>
                      <p class="mt-1">{{ batchDetails.species ? batchDetails.species.name : 'Unknown' }}</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Lifecycle Stage</h3>
                      <p class="mt-1">{{ batchDetails.lifecycle_stage ? batchDetails.lifecycle_stage.name : 'Unknown' }}</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Population Count</h3>
                      <p class="mt-1">{{ batchDetails.population_count }}</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Biomass</h3>
                      <p class="mt-1">{{ batchDetails.biomass_kg }} kg</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Average Weight</h3>
                      <p class="mt-1">{{ batchDetails.avg_weight_g }} g</p>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Start Date</h3>
                      <p class="mt-1">{{ formatDate(batchDetails.start_date) }}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Container assignments section -->
              <div>
                <h3 class="text-md font-semibold mb-3">Container Assignments</h3>
                <div class="bg-white shadow rounded-lg overflow-hidden">
                  <table v-if="batchDetails.container_assignments && batchDetails.container_assignments.length > 0" 
                        class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Container</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Population</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Biomass</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assignment Date</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr v-for="assignment in batchDetails.container_assignments" :key="assignment.id">
                        <td class="px-6 py-4 whitespace-nowrap">
                          <div class="font-medium text-gray-900">
                            {{ assignment.container ? assignment.container.name : 'Unknown container' }}
                          </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ assignment.population_count }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ assignment.biomass_kg }} kg
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ formatDate(assignment.assignment_date) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-else class="p-4 text-center text-gray-500">
                    No container assignments found for this batch.
                  </div>
                </div>
              </div>
              
              <!-- Growth samples section -->
              <div>
                <h3 class="text-md font-semibold mb-3">Growth Samples</h3>
                <div class="bg-white shadow rounded-lg overflow-hidden">
                  <table v-if="batchDetails.growth_samples && batchDetails.growth_samples.length > 0" 
                        class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sample Size</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Weight (g)</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Length (cm)</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr v-for="sample in batchDetails.growth_samples" :key="sample.id">
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ formatDate(sample.sample_date) }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ sample.sample_size }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ sample.avg_weight_g }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          {{ sample.avg_length_cm || 'N/A' }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-else class="p-4 text-center text-gray-500">
                    No growth samples found for this batch.
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Timeline view -->
            <div v-else-if="batchDetails && activeTab === 'timeline'" class="mt-4">
              <BatchTimeline :batchId="selectedBatch.id" />
            </div>
            
            <!-- No batch details found state -->
            <div v-else-if="!batchDetails" class="bg-white shadow rounded-lg p-6 text-center text-gray-500">
              Failed to load batch details.
            </div>
          </div>
          
          <!-- No batch selected state -->
          <div v-else class="bg-white shadow rounded-lg p-6 text-center text-gray-500">
            Select a batch to view details.
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
