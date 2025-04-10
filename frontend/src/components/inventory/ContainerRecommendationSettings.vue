<template>
  <div class="container-settings">
    <h3 class="settings-title">Container Feed Recommendation Settings</h3>
    
    <div class="alert info" v-if="!loaded">
      <p>Loading container settings...</p>
    </div>
    
    <div class="alert error" v-if="error">
      <p>{{ error }}</p>
    </div>
    
    <div class="settings-table" v-if="loaded && !error">
      <div v-if="containers.length === 0" class="no-data">
        <p>No containers found in the system.</p>
      </div>
      
      <table v-else>
        <thead>
          <tr>
            <th>Container</th>
            <th>Type</th>
            <th>Location</th>
            <th>Feed Recommendations</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="container in containers" :key="container.id">
            <td>{{ container.name }}</td>
            <td>{{ container.container_type_name }}</td>
            <td>{{ container.location_name || 'Unknown' }}</td>
            <td>
              <div class="toggle-container">
                <label class="switch">
                  <input 
                    type="checkbox" 
                    :checked="container.feed_recommendations_enabled"
                    @change="toggleRecommendations(container)"
                    :disabled="isToggling"
                  >
                  <span class="slider round"></span>
                </label>
                <span class="toggle-label">
                  {{ container.feed_recommendations_enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'ContainerRecommendationSettings',
  setup() {
    const containers = ref([])
    const loaded = ref(false)
    const error = ref(null)
    const isToggling = ref(false)
    
    const loadContainers = async () => {
      try {
        error.value = null
        const response = await axios.get('/api/v1/infrastructure/containers/')
        containers.value = response.data || []
        loaded.value = true
      } catch (err) {
        console.error('Error loading containers:', err)
        error.value = 'Failed to load containers. Please try again.'
        loaded.value = true
      }
    }
    
    const toggleRecommendations = async (container) => {
      if (isToggling.value) return
      
      isToggling.value = true
      try {
        const newStatus = !container.feed_recommendations_enabled
        
        await axios.patch(`/api/v1/infrastructure/containers/${container.id}/`, {
          feed_recommendations_enabled: newStatus
        })
        
        // Update locally
        container.feed_recommendations_enabled = newStatus
      } catch (err) {
        console.error('Error updating container settings:', err)
        alert('Failed to update recommendation settings. Please try again.')
        // Revert UI change since API call failed
        container.feed_recommendations_enabled = !container.feed_recommendations_enabled
      } finally {
        isToggling.value = false
      }
    }
    
    onMounted(() => {
      loadContainers()
    })
    
    return {
      containers,
      loaded,
      error,
      isToggling,
      toggleRecommendations
    }
  }
}
</script>

<style scoped>
.container-settings {
  background-color: white;
  border-radius: 6px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-title {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 20px;
  color: #0056b3;
}

.settings-table {
  margin-top: 15px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

tr:hover {
  background-color: #f8f9fa;
}

.toggle-container {
  display: flex;
  align-items: center;
}

.toggle-label {
  margin-left: 10px;
  font-size: 0.9rem;
}

/* Toggle Switch */
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.switch input { 
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
}

input:checked + .slider {
  background-color: #0056b3;
}

input:focus + .slider {
  box-shadow: 0 0 1px #0056b3;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

/* Rounded sliders */
.slider.round {
  border-radius: 24px;
}

.slider.round:before {
  border-radius: 50%;
}

.alert {
  padding: 12px 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.alert.info {
  background-color: #e7f3fe;
  border: 1px solid #cce5ff;
  color: #004085;
}

.alert.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.no-data {
  text-align: center;
  padding: 30px;
  background-color: #f9f9f9;
  border-radius: 4px;
  color: #6c757d;
}
</style>
