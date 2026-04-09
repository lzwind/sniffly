/**
 * Share Storage Module
 * Manages server addresses and authentication tokens in browser LocalStorage
 */

const ShareStorage = {
    KEYS: {
        SERVERS: 'sniffly_servers',
        TOKENS: 'sniffly_tokens',
        AUTH: 'sniffly_auth'
    },

    /**
     * Get list of saved servers
     * @returns {Array} Array of server objects {name, url}
     */
    getServers() {
        try {
            return JSON.parse(localStorage.getItem(this.KEYS.SERVERS) || '[]');
        } catch (e) {
            console.error('Error reading servers from LocalStorage:', e);
            return [];
        }
    },

    /**
     * Save a new server to the list
     * @param {string} url - Server URL
     * @param {string} name - Optional server name
     */
    saveServer(url, name = null) {
        if (!url) return;

        const servers = this.getServers();
        const existingIndex = servers.findIndex(s => s.url === url);

        const serverData = {
            name: name || url,
            url: url,
            lastUsed: new Date().toISOString()
        };

        if (existingIndex >= 0) {
            // Update existing server
            servers[existingIndex] = serverData;
        } else {
            // Add new server
            servers.push(serverData);
        }

        try {
            localStorage.setItem(this.KEYS.SERVERS, JSON.stringify(servers));
        } catch (e) {
            console.error('Error saving server to LocalStorage:', e);
        }
    },

    /**
     * Remove a server from the list
     * @param {string} url - Server URL to remove
     */
    removeServer(url) {
        const servers = this.getServers().filter(s => s.url !== url);
        try {
            localStorage.setItem(this.KEYS.SERVERS, JSON.stringify(servers));
        } catch (e) {
            console.error('Error removing server from LocalStorage:', e);
        }
    },

    /**
     * Get stored token for a server
     * @param {string} serverUrl - Server URL
     * @returns {Object|null} Token data {token, expiresAt} or null
     */
    getToken(serverUrl) {
        try {
            const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
            const tokenData = tokens[serverUrl];

            if (!tokenData) return null;

            // Check if token is expired
            if (tokenData.expiresAt && new Date(tokenData.expiresAt) < new Date()) {
                // Token expired, remove it
                this.removeToken(serverUrl);
                return null;
            }

            return tokenData;
        } catch (e) {
            console.error('Error reading token from LocalStorage:', e);
            return null;
        }
    },

    /**
     * Save token for a server
     * @param {string} serverUrl - Server URL
     * @param {string} token - JWT token
     * @param {number} expiresIn - Token expiration time in seconds
     */
    saveToken(serverUrl, token, expiresIn) {
        if (!serverUrl || !token) return;

        try {
            const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
            const expiresAt = new Date(Date.now() + expiresIn * 1000).toISOString();

            tokens[serverUrl] = {
                token: token,
                expiresAt: expiresAt,
                savedAt: new Date().toISOString()
            };

            localStorage.setItem(this.KEYS.TOKENS, JSON.stringify(tokens));
        } catch (e) {
            console.error('Error saving token to LocalStorage:', e);
        }
    },

    /**
     * Remove token for a server
     * @param {string} serverUrl - Server URL
     */
    removeToken(serverUrl) {
        try {
            const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
            delete tokens[serverUrl];
            localStorage.setItem(this.KEYS.TOKENS, JSON.stringify(tokens));
        } catch (e) {
            console.error('Error removing token from LocalStorage:', e);
        }
    },

    /**
     * Clear all stored data (for logout)
     */
    clearAll() {
        try {
            localStorage.removeItem(this.KEYS.TOKENS);
        } catch (e) {
            console.error('Error clearing tokens from LocalStorage:', e);
        }
    },

    /**
     * Save complete auth information
     * @param {string} serverUrl - Server URL
     * @param {string} username - Username
     * @param {string} token - JWT token
     * @param {number} expiresIn - Token expiration time in seconds (default: 7 days)
     */
    saveAuth(serverUrl, username, token, expiresIn = 604800) {
        if (!serverUrl || !username || !token) return;

        try {
            const expiresAt = new Date(Date.now() + expiresIn * 1000).toISOString();
            const authData = {
                serverUrl: serverUrl,
                username: username,
                token: token,
                expiresAt: expiresAt,
                savedAt: new Date().toISOString()
            };
            localStorage.setItem(this.KEYS.AUTH, JSON.stringify(authData));
        } catch (e) {
            console.error('Error saving auth to LocalStorage:', e);
        }
    },

    /**
     * Get stored auth information
     * @returns {Object|null} Auth data {serverUrl, username, token, expiresAt} or null if expired/not found
     */
    getAuth() {
        try {
            const authData = JSON.parse(localStorage.getItem(this.KEYS.AUTH));
            if (!authData) return null;

            // Check if token is expired
            if (authData.expiresAt && new Date(authData.expiresAt) < new Date()) {
                // Token expired, clear it
                this.clearAuth();
                return null;
            }

            return authData;
        } catch (e) {
            console.error('Error reading auth from LocalStorage:', e);
            return null;
        }
    },

    /**
     * Clear stored auth information
     */
    clearAuth() {
        try {
            localStorage.removeItem(this.KEYS.AUTH);
        } catch (e) {
            console.error('Error clearing auth from LocalStorage:', e);
        }
    },

    /**
     * Refresh auth expiration timestamp (called after successful share)
     * @param {number} expiresIn - Token expiration time in seconds (default: 7 days)
     */
    refreshAuthTimestamp(expiresIn = 604800) {
        try {
            const authData = JSON.parse(localStorage.getItem(this.KEYS.AUTH));
            if (!authData) return;

            authData.expiresAt = new Date(Date.now() + expiresIn * 1000).toISOString();
            localStorage.setItem(this.KEYS.AUTH, JSON.stringify(authData));
        } catch (e) {
            console.error('Error refreshing auth timestamp:', e);
        }
    }
};

// Make available globally
window.ShareStorage = ShareStorage;
