<template>
  <div class="batch-timeline">
    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-8">
      <div class="animate-pulse text-blue-600">Loading timeline data...</div>
    </div>
    
    <!-- Error state -->
    <div v-else-if="error" class="bg-red-100 border-l-4 border-red-500 p-4 mb-5">
      <p class="text-red-700">{{ error }}</p>
    </div>
    
    <!-- Timeline content -->
    <div v-else>
      <!-- Timeline filters -->
      <div class="mb-4 flex flex-wrap gap-2">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">Event Types</label>
          <select
            v-model="filters.eventType"
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="all">All Events</option>
            <option value="transfer">Transfers</option>
            <option value="mortality">Mortality Events</option>
            <option value="growth">Growth Samples</option>
          </select>
        </div>
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">Time Range</label>
          <select
            v-model="filters.timeRange"
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="all">All Time</option>
            <option value="last30">Last 30 Days</option>
            <option value="last90">Last 90 Days</option>
            <option value="custom">Custom Range</option>
          </select>
        </div>
        <div v-if="filters.timeRange === 'custom'" class="flex flex-wrap gap-2 w-full">
          <div class="flex-1 min-w-[200px]">
            <label class="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
            <input
              type="date"
              v-model="filters.startDate"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          <div class="flex-1 min-w-[200px]">
            <label class="block text-sm font-medium text-gray-700 mb-1">End Date</label>
            <input
              type="date"
              v-model="filters.endDate"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-if="!hasEvents" class="bg-white shadow rounded-lg p-6 text-center text-gray-500">
        No events found for the selected filters.
      </div>
      
      <!-- Timeline visualization -->
      <div v-else class="timeline-container bg-white shadow rounded-lg p-6">
        <div v-if="batchInfo" class="mb-4 pb-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold">{{ batchInfo.batch_number }}</h3>
          <div class="flex flex-wrap gap-x-6 text-sm text-gray-600">
            <div>Species: <span class="font-medium">{{ batchInfo.species_name }}</span></div>
            <div>Stage: <span class="font-medium">{{ batchInfo.lifecycle_stage_name }}</span></div>
            <div>Status: 
              <span 
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" 
                :class="getStatusClass(batchInfo.status)"
              >
                {{ batchInfo.status }}
              </span>
            </div>
          </div>
        </div>
        
        <div class="relative">
          <!-- Timeline axis -->
          <div class="absolute left-2 top-0 bottom-0 w-0.5 bg-blue-200"></div>
          
          <!-- Timeline events -->
          <div class="space-y-8 relative ml-10">
            <div 
              v-for="(event, index) in filteredEvents" 
              :key="index"
              class="timeline-event relative"
            >
              <!-- Event node -->
              <div 
                class="absolute -left-10 mt-1.5 w-5 h-5 rounded-full border-4 z-10"
                :class="getEventNodeClass(event.type)"
              ></div>
              
              <!-- Event content -->
              <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm relative">
                <!-- Event date and type -->
                <div class="flex justify-between items-start mb-2">
                  <div class="font-semibold text-gray-900">{{ formatEventType(event.type) }}</div>
                  <div class="text-sm text-gray-500">{{ formatDate(event.date) }}</div>
                </div>
                
                <!-- Event details -->
                <div class="text-sm text-gray-700">
                  <!-- Transfer event -->
                  <div v-if="event.type === 'transfer'" class="space-y-2">
                    <div><span class="font-medium">Transfer Type:</span> {{ event.details.transfer_type_display }}</div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4">
                      <div>
                        <div class="text-xs uppercase text-gray-500 font-medium">Source</div>
                        <div>{{ event.details.source_container_name || 'N/A' }}</div>
                        <div>{{ event.details.source_lifecycle_stage_name }}</div>
                        <div>{{ event.details.source_count }} fish ({{ event.details.source_biomass_kg }} kg)</div>
                      </div>
                      <div>
                        <div class="text-xs uppercase text-gray-500 font-medium">Destination</div>
                        <div>{{ event.details.destination_container_name || 'N/A' }}</div>
                        <div>{{ event.details.destination_lifecycle_stage_name || event.details.source_lifecycle_stage_name }}</div>
                        <div>{{ event.details.transferred_count }} fish ({{ event.details.transferred_biomass_kg }} kg)</div>
                      </div>
                    </div>
                    <div v-if="event.details.mortality_count > 0" class="mt-2 text-red-600">
                      Mortalities during transfer: {{ event.details.mortality_count }}
                    </div>
                  </div>
                  
                  <!-- Mortality event -->
                  <div v-else-if="event.type === 'mortality'" class="space-y-1">
                    <div><span class="font-medium">Count:</span> {{ event.details.count }} fish</div>
                    <div><span class="font-medium">Biomass:</span> {{ event.details.biomass_kg }} kg</div>
                    <div><span class="font-medium">Cause:</span> {{ event.details.cause_display }}</div>
                    <div v-if="event.details.description"><span class="font-medium">Notes:</span> {{ event.details.description }}</div>
                  </div>
                  
                  <!-- Growth sample event -->
                  <div v-else-if="event.type === 'growth'" class="space-y-1">
                    <div><span class="font-medium">Sample Size:</span> {{ event.details.sample_size }} fish</div>
                    <div><span class="font-medium">Average Weight:</span> {{ event.details.avg_weight_g }} g</div>
                    <div v-if="event.details.avg_length_cm">
                      <span class="font-medium">Average Length:</span> {{ event.details.avg_length_cm }} cm
                    </div>
                    <div v-if="event.details.condition_factor">
                      <span class="font-medium">Condition Factor:</span> {{ event.details.condition_factor }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  batchId: {
    type: [Number, String],
    required: true
  }
})

const api = useApi()
const loading = ref(true)
const error = ref(null)
const batchInfo = ref(null)
const transfers = ref([])
const mortalityEvents = ref([])
const growthSamples = ref([])
const filters = ref({
  eventType: 'all',
  timeRange: 'all',
  startDate: null,
  endDate: null
})

// Computed property for all timeline events
const allEvents = computed(() => {
  // Transform transfers into events
  const transferEvents = transfers.value.map(t => ({
    type: 'transfer',
    date: t.transfer_date,
    details: t
  }))
  
  // Transform mortality events
  const mortalityEventsData = mortalityEvents.value.map(m => ({
    type: 'mortality',
    date: m.event_date,
    details: m
  }))
  
  // Transform growth samples
  const growthEvents = growthSamples.value.map(g => ({
    type: 'growth',
    date: g.sample_date,
    details: g
  }))
  
  // Combine all events and sort by date (newest first)
  return [...transferEvents, ...mortalityEventsData, ...growthEvents]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
})

// Apply filters to events
const filteredEvents = computed(() => {
  let result = allEvents.value

  // Filter by event type
  if (filters.value.eventType !== 'all') {
    result = result.filter(event => event.type === filters.value.eventType)
  }

  // Filter by time range
  if (filters.value.timeRange !== 'all') {
    const today = new Date()
    
    if (filters.value.timeRange === 'last30') {
      const cutoff = new Date(today)
      cutoff.setDate(today.getDate() - 30)
      result = result.filter(event => new Date(event.date) >= cutoff)
    } 
    else if (filters.value.timeRange === 'last90') {
      const cutoff = new Date(today)
      cutoff.setDate(today.getDate() - 90)
      result = result.filter(event => new Date(event.date) >= cutoff)
    } 
    else if (filters.value.timeRange === 'custom' && filters.value.startDate && filters.value.endDate) {
      const start = new Date(filters.value.startDate)
      const end = new Date(filters.value.endDate)
      end.setDate(end.getDate() + 1) // Include the end date
      
      result = result.filter(event => {
        const eventDate = new Date(event.date)
        return eventDate >= start && eventDate <= end
      })
    }
  }

  return result
})

// Check if we have any events to display
const hasEvents = computed(() => filteredEvents.value.length > 0)

// Watch for prop changes to reload data
watch(() => props.batchId, () => {
  if (props.batchId) {
    fetchTimelineData()
  }
})

// Format date for display
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString(undefined, { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  })
}

// Format event type for display
function formatEventType(type) {
  const types = {
    'transfer': 'Batch Transfer',
    'mortality': 'Mortality Event',
    'growth': 'Growth Sample'
  }
  return types[type] || type
}

// Get status CSS class
function getStatusClass(status) {
  const statusClasses = {
    'ACTIVE': 'bg-green-100 text-green-800',
    'COMPLETED': 'bg-blue-100 text-blue-800',
    'TERMINATED': 'bg-gray-100 text-gray-800'
  }
  return statusClasses[status] || 'bg-gray-100 text-gray-800'
}

// Get event node CSS class
function getEventNodeClass(type) {
  const nodeClasses = {
    'transfer': 'border-blue-500 bg-blue-100',
    'mortality': 'border-red-500 bg-red-100',
    'growth': 'border-green-500 bg-green-100'
  }
  return nodeClasses[type] || 'border-gray-500 bg-gray-100'
}

// Fetch batch and timeline data
async function fetchTimelineData() {
  loading.value = true
  error.value = null
  
  try {
    // Fetch batch details
    const batchResponse = await api.get(`/batch/batches/${props.batchId}/`)
    batchInfo.value = batchResponse
    
    // Fetch all timeline-related data in parallel
    const [transfersResponse, mortalityResponse, growthResponse] = await Promise.all([
      api.get(`/batch/transfers/`, { params: { source_batch: props.batchId } }),
      api.get(`/batch/mortality-events/`, { params: { batch: props.batchId } }),
      api.get(`/batch/growth-samples/`, { params: { batch: props.batchId } })
    ])
    
    // Process the responses
    transfers.value = transfersResponse.results || transfersResponse
    mortalityEvents.value = mortalityResponse.results || mortalityResponse
    growthSamples.value = growthResponse.results || growthResponse
  } catch (err) {
    console.error('Failed to load timeline data:', err)
    error.value = 'Failed to load timeline data. Please try again later.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (props.batchId) {
    fetchTimelineData()
  }
})
</script>

<style scoped>
.timeline-event:last-child .timeline-line {
  display: none;
}
</style>
