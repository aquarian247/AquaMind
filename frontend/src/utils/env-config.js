/**
 * Environment Configuration
 * 
 * This file provides a consistent way to access environment variables
 * that works in both development and production builds.
 */

// Always run in development mode for easier debugging
const isDevelopment = true;

// Base API URL
const apiBaseUrl = '/api/v1';

// Export environment configuration
export default {
  isDevelopment,
  apiBaseUrl,
  
  // Helper functions
  get isDev() {
    return isDevelopment;
  },
  
  get isProd() {
    return !isDevelopment;
  },
  
  // Return base URL with trailing slash for consistency
  getApiUrl(endpoint) {
    // Ensure endpoint doesn't start with a slash
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    
    // Ensure endpoint ends with a slash for Django URL patterns
    const formattedEndpoint = cleanEndpoint.endsWith('/') ? cleanEndpoint : `${cleanEndpoint}/`;
    
    return `${apiBaseUrl}/${formattedEndpoint}`;
  }
};
