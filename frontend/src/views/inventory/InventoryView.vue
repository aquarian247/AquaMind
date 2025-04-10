<template>
  <AppLayout>
    <div class="inventory-container">
      <h1>Inventory Management</h1>
      
      <div class="section-tabs">
        <div 
          :class="['tab', activeSection === 'feed' ? 'active' : '']"
          @click="activeSection = 'feed'"
        >
          Feed
        </div>
        <div 
          :class="['tab', activeSection === 'recommendations' ? 'active' : '']"
          @click="activeSection = 'recommendations'"
        >
          Feed Recommendations
        </div>
        <div 
          :class="['tab', activeSection === 'settings' ? 'active' : '']"
          @click="activeSection = 'settings'"
        >
          Recommendation Settings
        </div>
        <div 
          :class="['tab', activeSection === 'feeding-events' ? 'active' : '']"
          @click="activeSection = 'feeding-events'"
        >
          Feeding Events
        </div>
      </div>
      
      <div class="section-content">
        <component :is="activeComponent"></component>
      </div>
    </div>
  </AppLayout>
</template>

<script>
import { ref, computed } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import FeedRecommendationsView from './FeedRecommendationsView.vue'
import ContainerRecommendationSettings from '@/components/inventory/ContainerRecommendationSettings.vue'

export default {
  name: 'InventoryView',
  components: {
    AppLayout,
    FeedRecommendationsView,
    ContainerRecommendationSettings
  },
  setup() {
    const activeSection = ref('recommendations') // Default to recommendations tab
    
    const activeComponent = computed(() => {
      switch (activeSection.value) {
        case 'recommendations':
          return FeedRecommendationsView
        case 'settings':
          return ContainerRecommendationSettings
        case 'feed':
          // To be implemented later
          return { template: '<div>Feed management will be implemented here</div>' }
        case 'feeding-events':
          // To be implemented later
          return { template: '<div>Feeding events will be implemented here</div>' }
        default:
          return FeedRecommendationsView
      }
    })
    
    return {
      activeSection,
      activeComponent
    }
  }
}
</script>

<style scoped>
.inventory-container {
  padding: 20px;
}

h1 {
  margin-bottom: 20px;
  color: #0056b3;
}

.section-tabs {
  display: flex;
  border-bottom: 1px solid #ddd;
  margin-bottom: 20px;
}

.tab {
  padding: 10px 20px;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
  margin-right: 5px;
  transition: all 0.2s ease;
}

.tab:hover {
  background-color: #f0f7ff;
}

.tab.active {
  background-color: #0056b3;
  color: white;
  border-bottom: 2px solid #0056b3;
}

.section-content {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  min-height: 400px;
}
</style>
