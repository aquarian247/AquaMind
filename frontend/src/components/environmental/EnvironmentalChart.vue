<script setup>
import { ref, onMounted, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  stationId: {
    type: [Number, String],
    default: null
  },
  containerId: {
    type: [Number, String],
    default: null
  },
  readingType: {
    type: String,
    default: 'temperature'
  },
  timeRange: {
    type: String,
    default: 'day' // 'day', 'week', 'month'
  }
})

const api = useApi()
const chartData = ref([])
const loading = ref(false)
const error = ref(null)

// Watch for prop changes to reload data
watch([() => props.stationId, () => props.containerId, () => props.readingType, () => props.timeRange], 
  () => {
    fetchEnvironmentalData()
  }
)

async function fetchEnvironmentalData() {
  if (!props.stationId && !props.containerId) return
  
  loading.value = true
  error.value = null
  
  try {
    // Build query parameters
    const params = {
      reading_type: props.readingType,
      time_range: props.timeRange
    }
    
    if (props.stationId) {
      params.station_id = props.stationId
    }
    
    if (props.containerId) {
      params.container_id = props.containerId
    }
    
    const response = await api.get('/environmental/readings/', { params })
    const results = response.results || response
    
    // Format data for chart
    chartData.value = results.map(item => ({
      timestamp: new Date(item.timestamp),
      value: item.value,
      unit: item.unit
    }))
  } catch (err) {
    error.value = 'Failed to load environmental data'
    console.error(err)
    chartData.value = []
  } finally {
    loading.value = false
  }
}

// Format the reading type for display
function formatReadingType(type) {
  const typeMap = {
    'temperature': 'Temperature',
    'dissolved_oxygen': 'Dissolved Oxygen',
    'ph': 'pH',
    'salinity': 'Salinity',
    'ammonia': 'Ammonia',
    'nitrite': 'Nitrite',
    'nitrate': 'Nitrate'
  }
  
  return typeMap[type] || type
}

// Calculate the Y-axis range based on data
function getYAxisRange() {
  if (!chartData.value.length) return { min: 0, max: 10 }
  
  const values = chartData.value.map(d => d.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const padding = (max - min) * 0.1
  
  return {
    min: Math.max(0, min - padding),
    max: max + padding
  }
}

// Get the unit for the current reading type
function getUnit() {
  if (!chartData.value.length) return ''
  
  const units = {
    'temperature': '°C',
    'dissolved_oxygen': 'mg/L',
    'ph': '',
    'salinity': 'ppt',
    'ammonia': 'mg/L',
    'nitrite': 'mg/L',
    'nitrate': 'mg/L'
  }
  
  return units[props.readingType] || chartData.value[0].unit || ''
}

// Format the date for display in the chart
function formatDate(date) {
  if (!date) return ''
  
  const options = {
    hour: '2-digit',
    minute: '2-digit'
  }
  
  if (props.timeRange === 'week' || props.timeRange === 'month') {
    options.month = 'short'
    options.day = 'numeric'
  }
  
  return date.toLocaleDateString(undefined, options)
}

onMounted(() => {
  fetchEnvironmentalData()
})
</script>

<template>
  <div class="environmental-chart-container">
    <div class="chart-header flex justify-between items-center mb-4">
      <h3 class="text-lg font-medium">{{ formatReadingType(readingType) }} Readings</h3>
      <div class="text-sm text-gray-500">{{ getUnit() }}</div>
    </div>
    
    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-6">
      <div class="animate-pulse text-blue-600">Loading data...</div>
    </div>
    
    <!-- Error state -->
    <div v-else-if="error" class="text-red-500 py-4">
      {{ error }}
    </div>
    
    <!-- Empty state -->
    <div v-else-if="chartData.length === 0" class="text-gray-500 py-4 text-center">
      No data available for the selected parameters.
    </div>
    
    <!-- Chart -->
    <div v-else class="chart-area" style="height: 200px; position: relative;">
      <!-- Simple chart mockup using HTML/CSS -->
      <div class="chart-mock relative h-full flex items-end">
        <template v-for="(point, index) in chartData" :key="index">
          <div 
            class="chart-bar bg-blue-500 hover:bg-blue-600 transition-colors"
            :style="{
              height: `${((point.value - getYAxisRange().min) / (getYAxisRange().max - getYAxisRange().min)) * 100}%`,
              width: `${Math.max(5, 100 / chartData.length - 2)}%`,
              marginLeft: index === 0 ? '0' : '2px'
            }"
            :title="`${formatDate(point.timestamp)}: ${point.value} ${getUnit()}`"
          ></div>
        </template>
      </div>
      
      <!-- Chart axis label -->
      <div class="chart-x-axis flex justify-between text-xs text-gray-500 mt-2">
        <span>{{ chartData.length > 0 ? formatDate(chartData[0].timestamp) : '' }}</span>
        <span>{{ chartData.length > 0 ? formatDate(chartData[chartData.length - 1].timestamp) : '' }}</span>
      </div>
    </div>
    
    <!-- Chart legend -->
    <div v-if="chartData.length > 0" class="chart-legend flex justify-between text-xs text-gray-500 mt-4">
      <span>Min: {{ Math.min(...chartData.map(d => d.value)).toFixed(1) }} {{ getUnit() }}</span>
      <span>Avg: {{ (chartData.reduce((sum, d) => sum + d.value, 0) / chartData.length).toFixed(1) }} {{ getUnit() }}</span>
      <span>Max: {{ Math.max(...chartData.map(d => d.value)).toFixed(1) }} {{ getUnit() }}</span>
    </div>
  </div>
</template>

<style scoped>
.chart-mock {
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.chart-bar {
  transition: height 0.3s ease;
  border-radius: 2px 2px 0 0;
}
</style>
