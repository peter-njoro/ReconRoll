
class SessionDetailManager {
    constructor(sessionId, isDevMode, urls) {
        this.sessionId = sessionId;
        this.isDevMode = isDevMode;
        this.urls = urls;
        this.refreshInterval = null;
    }

    startAutoRefresh() {
        const refreshRate = this.isDevMode ? 3000 : 2000; // slower refresh in dev mode
        this.refreshInterval = setInterval(() => this.refreshAll(), refreshRate);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    refreshAll() {
        this.refreshStats();
        this.refreshEvents();
        this.refreshPresentStudents();
        this.refreshAbsentStudents();
        this.refreshUnknownFaces();
    }

    async refreshStats() {
        try {
            const response = await fetch(this.urls.stats);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            document.getElementById('present-count').textContent = data.present_count;
            document.getElementById('total-expected').textContent = data.total_expected;
            document.getElementById('unknown-count').textContent = data.unknown_count;
        } catch (error) {
            this.handleError(error, 'refreshing statistics');
        }
    }

    async refreshEvents() {
        await this.refreshHtml(this.urls.events, 'events-list', 'events');
    }

    async refreshPresentStudents() {
        await this.refreshHtml(this.urls.present, 'present-students-list', 'present students');
    }

    async refreshAbsentStudents() {
        await this.refreshHtml(this.urls.absent, 'absent-students-list', 'absent students');
    }

    async refreshUnknownFaces() {
        await this.refreshHtml(this.urls.unknown, 'unknown-faces-list', 'unknown faces');
    }

    async refreshHtml(url, elementId, context) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const html = await response.text();
            const container = document.getElementById(elementId);
            if (container) container.innerHTML = html;
        } catch (error) {
            this.handleError(error, `refreshing ${context}`);
        }
    }

    showNotification(message, type = 'info') {
        // You could wire this up to Bootstrap alerts/toasts
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    handleError(error, context) {
        console.error(`Error in ${context}:`, error);
        this.showNotification(`Error ${context}. Please try again.`, 'error');
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

// -----------------------------
// ✅ Initialization
// -----------------------------
let sessionManager = null;

document.addEventListener('DOMContentLoaded', function () {
    if (!window.SESSION_CONFIG || !window.SESSION_URLS) {
        console.warn("Session config or URLs missing. Skipping SessionDetailManager init.");
        return;
    }

    if (window.SESSION_CONFIG.status === 'ongoing') {
        sessionManager = new SessionDetailManager(
            window.SESSION_CONFIG.id,
            window.SESSION_CONFIG.isDevMode,
            window.SESSION_URLS
        );
        sessionManager.startAutoRefresh();
    }

    // Attach manual refresh buttons via data-action attributes
    document.querySelectorAll('[data-refresh]').forEach(button => {
        button.addEventListener('click', () => {
            if (!sessionManager) return;
            const action = button.dataset.refresh;
            const method = `refresh${action.charAt(0).toUpperCase()}${action.slice(1)}`;
            if (typeof sessionManager[method] === 'function') {
                sessionManager[method]();
            }
        });
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (sessionManager) {
        sessionManager.destroy();
        sessionManager = null;
    }
});
