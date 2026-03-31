/**
 * Share Storage Module
 * Manages server addresses and tokens in LocalStorage
 */
const ShareStorage = {
    // Keys for LocalStorage
    KEYS: {
        SERVERS: 'sniffly_servers',
        TOKENS: 'sniffly_tokens'
    },

    /**
     * Get list of saved servers
     * @returns {Array} Array of server objects {url, name, last_used}
     */
    getServers() {
        const data = localStorage.getItem(this.KEYS.SERVERS);
        return data ? JSON.parse(data) : [];
    },

    /**
     * Save a server to the list
     * @param {string} url - Server URL
     * @param {string} name - Server name (optional)
     */
    saveServer(url, name = null) {
        const servers = this.getServers();
        const existingIndex = servers.findIndex(s => s.url === url);

        const serverData = {
            url,
            name: name || url,
            last_used: new Date().toISOString()
        };

        if (existingIndex >= 0) {
            servers[existingIndex] = serverData;
        } else {
            servers.push(serverData);
        }

        localStorage.setItem(this.KEYS.SERVERS, JSON.stringify(servers));
    },

    /**
     * Remove a server from the list
     * @param {string} url - Server URL to remove
     */
    removeServer(url) {
        const servers = this.getServers().filter(s => s.url !== url);
        localStorage.setItem(this.KEYS.SERVERS, JSON.stringify(servers));
        // Also remove any stored token for this server
        this.removeToken(url);
    },

    /**
     * Get stored token for a server
     * @param {string} serverUrl - Server URL
     * @returns {Object|null} Token data {token, expires_at} or null
     */
    getToken(serverUrl) {
        const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
        const tokenData = tokens[serverUrl];

        if (!tokenData) return null;

        // Check if token is expired
        if (tokenData.expires_at) {
            const expiresAt = new Date(tokenData.expires_at);
            if (expiresAt < new Date()) {
                // Token expired, remove it
                this.removeToken(serverUrl);
                return null;
            }
        }

        return tokenData;
    },

    /**
     * Save token for a server
     * @param {string} serverUrl - Server URL
     * @param {string} token - JWT token
     * @param {number} expiresIn - Expiration time in seconds
     */
    saveToken(serverUrl, token, expiresIn) {
        const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
        const expiresAt = new Date(Date.now() + expiresIn * 1000);

        tokens[serverUrl] = {
            token,
            expires_at: expiresAt.toISOString()
        };

        localStorage.setItem(this.KEYS.TOKENS, JSON.stringify(tokens));
    },

    /**
     * Remove token for a server
     * @param {string} serverUrl - Server URL
     */
    removeToken(serverUrl) {
        const tokens = JSON.parse(localStorage.getItem(this.KEYS.TOKENS) || '{}');
        delete tokens[serverUrl];
        localStorage.setItem(this.KEYS.TOKENS, JSON.stringify(tokens));
    },

    /**
     * Clear all stored data
     */
    clearAll() {
        localStorage.removeItem(this.KEYS.SERVERS);
        localStorage.removeItem(this.KEYS.TOKENS);
    }
};

// Make available globally
window.ShareStorage = ShareStorage;
