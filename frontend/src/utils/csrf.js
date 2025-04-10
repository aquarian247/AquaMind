/**
 * CSRF token handling utility for AquaMind
 * Handles getting Django CSRF tokens and ensuring they're included in request headers
 */

// Function to get the CSRF token from cookies
export function getCSRFToken() {
  // Check for the Django CSRF cookie
  let csrfToken = null;
  const cookies = document.cookie.split(';');
  
  for (let cookie of cookies) {
    const trimmedCookie = cookie.trim();
    // Django uses csrftoken as the cookie name
    if (trimmedCookie.startsWith('csrftoken=')) {
      csrfToken = trimmedCookie.substring('csrftoken='.length);
      break;
    }
  }
  
  return csrfToken;
}

// Function to fetch a new CSRF token from the Django server
export async function fetchCSRFToken() {
  try {
    // Make a GET request to the Django server to get a new CSRF token
    // This will set the CSRF cookie
    const response = await fetch('/api/csrf/', {
      method: 'GET',
      credentials: 'include' // Important: include cookies
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch CSRF token');
    }
    
    // The token is now in the cookies, extract it
    return getCSRFToken();
  } catch (error) {
    console.error('Error fetching CSRF token:', error);
    return null;
  }
}

// Function to set up Axios with CSRF token
export function setupCSRF(axiosInstance) {
  // Add request interceptor to include CSRF token in all non-GET requests
  axiosInstance.interceptors.request.use(
    async (config) => {
      // Only add CSRF token for state-changing methods (not GET or HEAD)
      if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
        let token = getCSRFToken();
        
        // If no token is found, try to fetch a new one
        if (!token) {
          token = await fetchCSRFToken();
        }
        
        // Set the CSRF token header if we have one
        if (token) {
          config.headers['X-CSRFToken'] = token;
        } else {
          console.warn('No CSRF token available for request:', config.url);
        }
      }
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  
  return axiosInstance;
}
