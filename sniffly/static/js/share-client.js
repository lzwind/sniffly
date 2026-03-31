/**
 * Share Client Module
 * Handles communication with internal Sniffly share server
 */
const ShareClient = {
    /**
     * Login to the server and get JWT token
     * @param {string} serverUrl - Server URL (e.g., http://10.0.1.100:8080)
     * @param {string} username - Username
     * @param {string} password - Password
     * @returns {Promise<Object>} Login result {success, token, expires_in, error}
     */
    async login(serverUrl, username, password) {
        try {
            const response = await fetch(`${serverUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                return {
                    success: false,
                    error: error.detail || `Login failed: ${response.status}`
                };
            }

            const data = await response.json();

            // Save token to storage
            if (window.ShareStorage && data.access_token) {
                window.ShareStorage.saveToken(serverUrl, data.access_token, data.expires_in);
                window.ShareStorage.saveServer(serverUrl);
            }

            return {
                success: true,
                token: data.access_token,
                expires_in: data.expires_in
            };
        } catch (error) {
            return {
                success: false,
                error: error.message || 'Network error'
            };
        }
    },

    /**
     * Get valid token for server (from cache or login)
     * @param {string} serverUrl - Server URL
     * @param {string} username - Username (for re-login if needed)
     * @param {string} password - Password (for re-login if needed)
     * @returns {Promise<string|null>} Valid token or null
     */
    async getValidToken(serverUrl, username, password) {
        // Check cached token first
        if (window.ShareStorage) {
            const cached = window.ShareStorage.getToken(serverUrl);
            if (cached && cached.token) {
                return cached.token;
            }
        }

        // No valid token, login
        const result = await this.login(serverUrl, username, password);
        return result.success ? result.token : null;
    },

    /**
     * Create a share on the server
     * @param {string} serverUrl - Server URL
     * @param {string} token - JWT token
     * @param {Object} shareData - Share data
     * @returns {Promise<Object>} Share result {success, url, share_id, error}
     */
    async createShare(serverUrl, token, shareData) {
        try {
            const response = await fetch(`${serverUrl}/api/shares`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(shareData)
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                return {
                    success: false,
                    error: error.detail || `Share failed: ${response.status}`
                };
            }

            const data = await response.json();
            return {
                success: true,
                url: data.url,
                share_id: data.share_id
            };
        } catch (error) {
            return {
                success: false,
                error: error.message || 'Network error'
            };
        }
    },

    /**
     * Test server connection
     * @param {string} serverUrl - Server URL
     * @returns {Promise<Object>} Test result {success, error}
     */
    async testConnection(serverUrl) {
        try {
            const response = await fetch(`${serverUrl}/health`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                return {
                    success: false,
                    error: `Server returned ${response.status}`
                };
            }

            return { success: true };
        } catch (error) {
            return {
                success: false,
                error: error.message || 'Cannot connect to server'
            };
        }
    }
};

// Make available globally
window.ShareClient = ShareClient;
