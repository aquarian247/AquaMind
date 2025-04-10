/**
 * Debug Logger
 * 
 * A utility for consistent logging and error tracking during development
 */

const DEBUG_LEVEL = {
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
  DEBUG: 'debug'
};

/**
 * Log a message to the console with a consistent format
 * @param {string} message - The message to log
 * @param {string} level - The log level (info, warn, error, debug)
 * @param {any} data - Optional data to include with the log
 */
export function logMessage(message, level = DEBUG_LEVEL.INFO, data = null) {
  const timestamp = new Date().toISOString();
  const prefix = `[AquaMind ${timestamp}]`;
  
  switch (level) {
    case DEBUG_LEVEL.WARN:
      console.warn(`${prefix} ${message}`, data || '');
      break;
    case DEBUG_LEVEL.ERROR:
      console.error(`${prefix} ${message}`, data || '');
      break;
    case DEBUG_LEVEL.DEBUG:
      console.debug(`${prefix} ${message}`, data || '');
      break;
    default:
      console.log(`${prefix} ${message}`, data || '');
  }
}

/**
 * Log an error and optional error details
 * @param {Error} error - The error object
 * @param {string} context - Where the error occurred
 * @param {any} additionalData - Optional additional data
 */
export function logError(error, context = 'Unknown', additionalData = null) {
  console.error(`[AquaMind ERROR] ${context}:`, error);
  if (additionalData) {
    console.error('Additional data:', additionalData);
  }
}

export default {
  log: logMessage,
  error: logError,
  DEBUG_LEVEL
};
