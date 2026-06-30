/* ============================================================
   Shared API Client — Civic Intelligence Platform
   ============================================================ */

const API = (() => {
  // Read from window.CIVIC_CONFIG if available, else default to localhost
  const MAIN_BASE = (window.CIVIC_CONFIG && window.CIVIC_CONFIG.MAIN_SERVICE_URL)
    ? window.CIVIC_CONFIG.MAIN_SERVICE_URL
    : 'http://localhost:5000';

  const PROCESSING_BASE = (window.CIVIC_CONFIG && window.CIVIC_CONFIG.PROCESSING_SERVICE_URL)
    ? window.CIVIC_CONFIG.PROCESSING_SERVICE_URL
    : 'http://localhost:5001';

  /**
   * Generic fetch wrapper with error handling.
   * @param {string} url
   * @param {RequestInit} options
   * @returns {Promise<any>}
   */
  async function request(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          'Accept': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
      }

      return data;
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error('Cannot connect to server. Please ensure the backend is running.');
      }
      throw err;
    }
  }

  /**
   * Submit a new complaint (multipart/form-data).
   * @param {FormData} formData
   */
  async function submitComplaint(formData) {
    return request(`${MAIN_BASE}/api/complaints`, {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type — browser sets it with boundary for FormData
    });
  }

  /**
   * Get list of complaints with filters.
   * @param {Object} params
   */
  async function getComplaints(params = {}) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== '' && v !== null && v !== undefined) qs.set(k, v); });
    return request(`${MAIN_BASE}/api/complaints?${qs}`);
  }

  /**
   * Get a single complaint by ID.
   * @param {string} id
   */
  async function getComplaint(id) {
    return request(`${MAIN_BASE}/api/complaints/${id}`);
  }

  /**
   * Update complaint status.
   * @param {string} id
   * @param {string} status
   */
  async function updateStatus(id, status) {
    return request(`${MAIN_BASE}/api/complaints/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
  }

  /**
   * Assign worker to complaint and send SMS.
   * @param {string} id
   * @param {string} workerName
   * @param {string} workerPhone
   */
  async function assignWorker(id, workerName, workerPhone) {
    return request(`${MAIN_BASE}/api/complaints/${id}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workerName, workerPhone }),
    });
  }

  /**
   * Get overall statistics.
   */
  async function getStats() {
    return request(`${MAIN_BASE}/api/stats`);
  }

  /**
   * Get department distribution.
   */
  async function getDepartmentStats() {
    return request(`${MAIN_BASE}/api/stats/department`);
  }

  /**
   * Get category distribution.
   */
  async function getCategoryStats() {
    return request(`${MAIN_BASE}/api/stats/category`);
  }

  /**
   * Get hotspot data for maps.
   */
  async function getHotspots() {
    return request(`${MAIN_BASE}/api/stats/hotspots`);
  }

  /**
   * Get top community heroes leaderboard.
   * @param {number} limit
   */
  async function getLeaderboard(limit = 10) {
    return request(`${MAIN_BASE}/api/users/leaderboard?limit=${limit}`);
  }

  /**
   * Get predictive maintenance predictions.
   */
  async function getPredictions() {
    return request(`${PROCESSING_BASE}/api/predictions`);
  }

  return {
    submitComplaint,
    getComplaints,
    getComplaint,
    updateStatus,
    assignWorker,
    getStats,
    getDepartmentStats,
    getCategoryStats,
    getHotspots,
    getLeaderboard,
    getPredictions,
  };
})();
