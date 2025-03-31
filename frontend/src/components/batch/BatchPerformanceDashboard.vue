<template>
  <div class="batch-performance-dashboard">
    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-8">
      <div class="animate-pulse text-blue-600">Loading performance data...</div>
    </div>
    
    <!-- Error state -->
    <div v-else-if="error" class="bg-red-100 border-l-4 border-red-500 p-4 mb-5">
      <p class="text-red-700">{{ error }}</p>
    </div>
    
    <!-- Dashboard content -->
    <div v-else class="space-y-6">
      <!-- Summary section -->
      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-4">Batch Performance Summary</h3>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-blue-50 p-4 rounded-lg">
            <div class="text-sm font-medium text-gray-500">Current Population</div>
            <div class="mt-1 text-2xl font-semibold">{{ metrics?.current_metrics?.population_count?.toLocaleString() || 'N/A' }}</div>
          </div>
          <div class="bg-green-50 p-4 rounded-lg">
            <div class="text-sm font-medium text-gray-500">Current Biomass</div>
            <div class="mt-1 text-2xl font-semibold">{{ formatNumber(metrics?.current_metrics?.biomass_kg) || 'N/A' }} kg</div>
          </div>
          <div class="bg-purple-50 p-4 rounded-lg">
            <div class="text-sm font-medium text-gray-500">Avg Weight</div>
            <div class="mt-1 text-2xl font-semibold">{{ formatNumber(metrics?.current_metrics?.avg_weight_g) || 'N/A' }} g</div>
          </div>
          <div class="bg-yellow-50 p-4 rounded-lg">
            <div class="text-sm font-medium text-gray-500">Days Active</div>
            <div class="mt-1 text-2xl font-semibold">{{ metrics?.days_active || 'N/A' }}</div>
          </div>
        </div>
      </div>
      
      <!-- Growth charts -->
      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-4">Growth Analysis</h3>
        <div v-if="!growthData.length" class="text-center text-gray-500 py-6">
          No growth samples available for this batch.
        </div>
        <div v-else>
          <!-- Weight over time chart -->
          <div class="h-64 mb-6">
            <canvas ref="weightChartRef"></canvas>
          </div>
          
          <!-- Growth rate chart -->
          <div v-if="growthData.length > 1" class="h-64">
            <canvas ref="growthRateChartRef"></canvas>
          </div>
          
          <!-- Growth summary -->
          <div v-if="growthSummary" class="mt-6 pt-6 border-t border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div class="text-sm font-medium text-gray-500">Total Weight Gain</div>
              <div class="mt-1 text-xl font-semibold">{{ formatNumber(growthSummary.total_weight_gain_g) }} g</div>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-500">Avg Daily Growth</div>
              <div class="mt-1 text-xl font-semibold">{{ formatNumber(growthSummary.avg_daily_growth_g) }} g/day</div>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-500">SGR (Specific Growth Rate)</div>
              <div class="mt-1 text-xl font-semibold">{{ formatNumber(growthSummary.avg_sgr) }}%</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Mortality Analysis -->
      <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-4">Mortality Analysis</h3>
        <div v-if="!metrics?.mortality_metrics?.total_count" class="text-center text-gray-500 py-6">
          No mortality events recorded for this batch.
        </div>
        <div v-else class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div class="text-sm font-medium text-gray-500">Total Mortality</div>
              <div class="mt-1 text-xl font-semibold">{{ metrics.mortality_metrics.total_count.toLocaleString() }}</div>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-500">Mortality Rate</div>
              <div class="mt-1 text-xl font-semibold">{{ formatNumber(metrics.mortality_metrics.mortality_rate) }}%</div>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-500">Total Biomass Loss</div>
              <div class="mt-1 text-xl font-semibold">{{ formatNumber(metrics.mortality_metrics.total_biomass_kg) }} kg</div>
            </div>
          </div>
          
          <!-- Mortality by cause -->
          <div v-if="metrics.mortality_metrics.by_cause.length">
            <h4 class="text-md font-medium mb-2">Mortality by Cause</h4>
            <div class="h-64">
              <canvas ref="mortalityChartRef"></canvas>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Container Metrics -->
      <div v-if="metrics?.container_metrics?.length" class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-semibold mb-4">Container Metrics</h3>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Container</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Population</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Biomass (kg)</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Density (kg/m³)</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(container, index) in metrics.container_metrics" :key="index">
                <td class="px-6 py-4 whitespace-nowrap">{{ container.container_name }}</td>
                <td class="px-6 py-4 whitespace-nowrap">{{ container.population.toLocaleString() }}</td>
                <td class="px-6 py-4 whitespace-nowrap">{{ formatNumber(container.biomass_kg) }}</td>
                <td class="px-6 py-4 whitespace-nowrap">{{ container.density_kg_m3 ? formatNumber(container.density_kg_m3) : 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import Chart from 'chart.js/auto'

const props = defineProps({
  batchId: {
    type: [Number, String],
    required: true
  }
})

const api = useApi()
const loading = ref(true)
const error = ref(null)
const metrics = ref(null)
const growthData = ref([])
const growthSummary = ref(null)

// Chart references
const weightChartRef = ref(null)
const growthRateChartRef = ref(null)
const mortalityChartRef = ref(null)

// Chart instances
let weightChart = null
let growthRateChart = null
let mortalityChart = null

// Format numbers with 2 decimal places
function formatNumber(value) {
  if (value === null || value === undefined) return null
  return parseFloat(value).toFixed(2)
}

// Fetch performance metrics
async function fetchPerformanceMetrics() {
  loading.value = true
  error.value = null
  
  try {
    const performanceResponse = await api.get(`/batch/batches/${props.batchId}/performance_metrics/`)
    metrics.value = performanceResponse
  } catch (err) {
    console.error('Failed to load performance metrics:', err)
    error.value = 'Failed to load performance metrics'
  }
}

// Fetch growth analysis data
async function fetchGrowthAnalysis() {
  try {
    const growthResponse = await api.get(`/batch/batches/${props.batchId}/growth_analysis/`)
    growthData.value = growthResponse.growth_metrics || []
    growthSummary.value = growthResponse.summary || null
    
    // Wait for DOM update before initializing charts
    setTimeout(() => {
      createWeightChart()
      createGrowthRateChart()
    }, 100)
  } catch (err) {
    console.error('Failed to load growth analysis:', err)
    // Don't set error here, we'll still show performance metrics if available
  } finally {
    loading.value = false
  }
}

// Create weight over time chart
function createWeightChart() {
  if (!weightChartRef.value || !growthData.value.length) return
  
  const ctx = weightChartRef.value.getContext('2d')
  
  // Clean up existing chart
  if (weightChart) {
    weightChart.destroy()
  }
  
  // Prepare data
  const labels = growthData.value.map(item => formatDate(item.date))
  const data = growthData.value.map(item => item.avg_weight_g)
  
  weightChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Average Weight (g)',
        data: data,
        fill: false,
        borderColor: 'rgb(79, 70, 229)',
        tension: 0.1,
        pointBackgroundColor: 'rgb(79, 70, 229)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          title: {
            display: true,
            text: 'Weight (g)'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      }
    }
  })
}

// Create growth rate chart
function createGrowthRateChart() {
  if (!growthRateChartRef.value || !growthData.value.length || growthData.value.length < 2) return
  
  const ctx = growthRateChartRef.value.getContext('2d')
  
  // Clean up existing chart
  if (growthRateChart) {
    growthRateChart.destroy()
  }
  
  // Filter to only samples with daily growth
  const samplesWithGrowth = growthData.value.filter(item => item.daily_growth_g !== undefined)
  
  if (samplesWithGrowth.length < 2) return
  
  // Prepare data
  const labels = samplesWithGrowth.map(item => formatDate(item.date))
  const dailyGrowthData = samplesWithGrowth.map(item => item.daily_growth_g)
  const sgrData = samplesWithGrowth.map(item => item.sgr)
  
  growthRateChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Daily Growth (g/day)',
          data: dailyGrowthData,
          backgroundColor: 'rgba(34, 197, 94, 0.6)',
          borderColor: 'rgb(34, 197, 94)',
          borderWidth: 1
        },
        {
          label: 'SGR (%)',
          data: sgrData,
          type: 'line',
          fill: false,
          borderColor: 'rgb(249, 115, 22)',
          backgroundColor: 'rgb(249, 115, 22)',
          tension: 0.1,
          pointBackgroundColor: 'rgb(249, 115, 22)',
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          title: {
            display: true,
            text: 'Daily Growth (g/day)'
          }
        },
        y1: {
          position: 'right',
          beginAtZero: false,
          title: {
            display: true,
            text: 'SGR (%)'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      }
    }
  })
}

// Create mortality by cause chart
function createMortalityChart() {
  if (!mortalityChartRef.value || !metrics.value?.mortality_metrics?.by_cause?.length) return
  
  const ctx = mortalityChartRef.value.getContext('2d')
  
  // Clean up existing chart
  if (mortalityChart) {
    mortalityChart.destroy()
  }
  
  // Prepare data
  const causes = metrics.value.mortality_metrics.by_cause.map(item => item.cause)
  const counts = metrics.value.mortality_metrics.by_cause.map(item => item.count)
  const backgroundColor = [
    'rgba(239, 68, 68, 0.7)',
    'rgba(249, 115, 22, 0.7)',
    'rgba(234, 179, 8, 0.7)',
    'rgba(16, 185, 129, 0.7)',
    'rgba(59, 130, 246, 0.7)',
    'rgba(139, 92, 246, 0.7)',
  ]
  
  mortalityChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: causes,
      datasets: [{
        data: counts,
        backgroundColor: backgroundColor.slice(0, causes.length),
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total * 100) * 10) / 10;
              return `${label}: ${value} (${percentage}%)`;
            }
          }
        }
      }
    }
  })
}

// Format date for display
function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

// Clean up charts on unmount
onUnmounted(() => {
  if (weightChart) weightChart.destroy()
  if (growthRateChart) growthRateChart.destroy()
  if (mortalityChart) mortalityChart.destroy()
})

// Watch for changes to props
watch(() => props.batchId, (newId) => {
  if (newId) {
    fetchPerformanceMetrics()
    fetchGrowthAnalysis()
  }
})

// Watch for mortality metrics to create the mortality chart
watch(() => metrics.value?.mortality_metrics, () => {
  // Wait for DOM update before initializing chart
  setTimeout(() => {
    createMortalityChart()
  }, 100)
}, { deep: true })

onMounted(() => {
  if (props.batchId) {
    fetchPerformanceMetrics()
    fetchGrowthAnalysis()
  }
})
</script>
