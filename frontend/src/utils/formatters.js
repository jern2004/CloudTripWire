/**
 * Utility functions for formatting data in the CloudTripwire dashboard
 */

/**
 * Format ISO timestamp to readable date and time
 * @param {string} isoString - ISO 8601 timestamp
 * @returns {string} Formatted date string
 */
export const formatTimestamp = (isoString) => {
  if (!isoString) return 'N/A';
  
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  // Show relative time if less than 24 hours ago
  if (diffMins < 60) {
    return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
  } else if (diffMins < 1440) {
    const hours = Math.floor(diffMins / 60);
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  }
  
  // Otherwise show full date
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

/**
 * Format date for chart display (shorter format)
 * @param {string} isoString - ISO 8601 timestamp
 * @returns {string} Short date format
 */
export const formatChartDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

/**
 * Truncate long strings with ellipsis
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated string
 */
export const truncateString = (str, maxLength = 50) => {
  if (!str) return '';
  return str.length > maxLength ? `${str.substring(0, maxLength)}...` : str;
};

/**
 * Get status badge color classes
 * @param {string} status - Status value ('Active' or 'Resolved')
 * @returns {string} Tailwind CSS classes
 */
export const getStatusColor = (status) => {
  return status === 'Active' ? 'status-active' : 'status-resolved';
};

/**
 * Get cloud provider badge color
 * @param {string} cloud - Cloud provider name
 * @returns {string} Tailwind CSS classes
 */
export const getCloudColor = (cloud) => {
  const colors = {
    AWS: 'bg-orange-500/20 text-orange-400 border-orange-500',
    Azure: 'bg-blue-500/20 text-blue-400 border-blue-500',
    GCP: 'bg-red-500/20 text-red-400 border-red-500',
  };
  return colors[cloud] || 'bg-gray-500/20 text-gray-400 border-gray-500';
};

/**
 * Format number with commas for thousands
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
export const formatNumber = (num) => {
  if (typeof num !== 'number') return '0';
  return num.toLocaleString('en-US');
};

/**
 * Calculate percentage change
 * @param {number} current - Current value
 * @param {number} previous - Previous value
 * @returns {object} Object with percentage and direction
 */
export const calculateChange = (current, previous) => {
  if (!previous) return { percent: 0, direction: 'neutral' };
  
  const change = ((current - previous) / previous) * 100;
  return {
    percent: Math.abs(change).toFixed(1),
    direction: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral'
  };
};