/**
 * Leaflet Map Picker for AquaMind
 * 
 * This script initializes a Leaflet map for selecting geographic coordinates
 * in the Django admin interface for Area and FreshwaterStation models.
 *
 * @author AquaMind Team
 * @version 1.0.0
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with our map container
    const mapContainer = document.getElementById('location-map');
    if (!mapContainer) return;

    // Get the input fields for latitude and longitude
    const container = document.getElementById('map-selector-container');
    const latField = document.getElementById(container.dataset.latField);
    const lngField = document.getElementById(container.dataset.lngField);
    
    if (!latField || !lngField) {
        console.error('Could not find latitude or longitude fields');
        return;
    }

    // Initialize the map with default center on Faroe Islands (61.5, -6.5)
    // Faroe Islands is a good default location for aquaculture installations
    const map = L.map('location-map').setView([61.5, -6.5], 8);

    // Add tile layers with attribution
    const baseMaps = {
        "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }),
        "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri, Maxar, Earthstar Geographics, and the GIS User Community'
        })
    };
    
    // Add the default layer to the map
    baseMaps["OpenStreetMap"].addTo(map);
    
    // Add layer control to switch between map types
    L.control.layers(baseMaps).addTo(map);
    
    // Add scale control
    L.control.scale().addTo(map);

    // Create a marker if coordinates already exist
    let marker;
    if (latField.value && lngField.value) {
        const lat = parseFloat(latField.value);
        const lng = parseFloat(lngField.value);
        if (!isNaN(lat) && !isNaN(lng)) {
            marker = L.marker([lat, lng], { draggable: true }).addTo(map);
            map.setView([lat, lng], 10);
            
            // Update fields when marker is dragged
            marker.on('dragend', updateCoordinateFields);
        }
    }

    /**
     * Updates the latitude and longitude fields with marker position
     * @param {Object} event - The dragend event from the marker
     */
    function updateCoordinateFields(event) {
        const position = marker.getLatLng();
        latField.value = position.lat.toFixed(6);
        lngField.value = position.lng.toFixed(6);
    }

    // Add a marker when the map is clicked
    map.on('click', function(e) {
        // Early return if we can't access the coordinates
        if (!e || !e.latlng) {
            console.error('Invalid click event or missing latlng');
            return;
        }
        
        // Remove existing marker if it exists
        if (marker) {
            map.removeLayer(marker);
        }
        
        // Create a new marker at the clicked position
        marker = L.marker(e.latlng, { draggable: true }).addTo(map);
        
        // Update the fields with the new coordinates
        latField.value = e.latlng.lat.toFixed(6);
        lngField.value = e.latlng.lng.toFixed(6);
        
        // Update fields when marker is dragged
        marker.on('dragend', updateCoordinateFields);
    });

    // Trigger a map resize after a short delay to ensure it's properly displayed
    setTimeout(function() {
        map.invalidateSize();
    }, 100);
});
