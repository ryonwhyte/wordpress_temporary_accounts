/**
 * WordPress Temporary Accounts - cPanel Frontend
 */

// State
let state = {
    selectedSite: null,
    wpInstalls: []
};

// API Communication
async function callAPI(action, payload = {}) {
    showLoading();

    try {
        const response = await fetch('../proxy.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, payload })
        });

        const data = await response.json();
        hideLoading();

        if (!data.ok) {
            throw new Error(data.error?.message || 'Unknown error');
        }

        return data.data;
    } catch (error) {
        hideLoading();
        showError(error.message);
        throw error;
    }
}

// UI Helpers
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    const errorBox = document.getElementById('error-message');
    errorBox.textContent = message;
    errorBox.style.display = 'block';
    setTimeout(() => {
        errorBox.style.display = 'none';
    }, 5000);
}

function hideSection(id) {
    document.getElementById(id).style.display = 'none';
}

function showSection(id) {
    document.getElementById(id).style.display = 'block';
}

// Health Check
async function checkHealth() {
    try {
        const health = await callAPI('health');
        const statusEl = document.getElementById('health-status');
        statusEl.textContent = `Daemon: ${health.status.toUpperCase()} (uptime: ${Math.floor(health.uptime_sec / 60)}m)`;
        statusEl.className = 'status ok';
    } catch (error) {
        const statusEl = document.getElementById('health-status');
        statusEl.textContent = 'Daemon: OFFLINE';
        statusEl.className = 'status error';
    }
}

// Scan for WordPress Installations
async function scanWordPress() {
    try {
        // For cPanel users, we don't need to pass cpanel_user - the proxy injects it
        state.wpInstalls = await callAPI('list_wp_installs', {});

        if (state.wpInstalls.length === 0) {
            showError('No WordPress installations found in your account');
            return;
        }

        displayWordPressInstalls();
        hideSection('result-section');
        hideSection('create-user-section');
    } catch (error) {
        console.error('Scan failed:', error);
    }
}

// Display WordPress Installations
function displayWordPressInstalls() {
    const list = document.getElementById('wp-installs-list');
    list.innerHTML = '';

    state.wpInstalls.forEach((install, index) => {
        const item = document.createElement('div');
        item.className = 'wp-install-item';
        item.dataset.index = index;

        item.innerHTML = `
            <div class="wp-install-path">${install.docroot}</div>
            <div class="wp-install-info">
                Database: ${install.db.name} | Table Prefix: ${install.table_prefix}
            </div>
        `;

        item.addEventListener('click', () => selectWordPress(index));
        list.appendChild(item);
    });
}

// Select WordPress Installation
function selectWordPress(index) {
    // Remove previous selection
    document.querySelectorAll('.wp-install-item').forEach(item => {
        item.classList.remove('selected');
    });

    // Mark as selected
    const selectedItem = document.querySelector(`[data-index="${index}"]`);
    selectedItem.classList.add('selected');

    state.selectedSite = state.wpInstalls[index];

    // Show create user section
    document.getElementById('selected-site').textContent = state.selectedSite.docroot;
    showSection('create-user-section');
    hideSection('result-section');
}

// Create Temporary User
async function createUser() {
    if (!state.selectedSite) {
        showError('Please select a WordPress installation first');
        return;
    }

    const role = document.getElementById('user-role').value;
    const expiryHours = parseInt(document.getElementById('expiry-hours').value);

    try {
        const result = await callAPI('create_temp_user', {
            site_path: state.selectedSite.docroot,
            role,
            expiry_hours: expiryHours
        });

        displayResult(result);
        showSection('result-section');
    } catch (error) {
        console.error('Create user failed:', error);
    }
}

// Display Result
function displayResult(result) {
    const expiryDate = new Date(result.expires_at * 1000);

    document.getElementById('result-details').innerHTML = `
        <strong>Login Credentials:</strong>
        <div style="margin-top:8px;">
            <strong>Username:</strong> <code>${result.user}</code><br>
            <strong>Password:</strong> <code>${result.temp_password}</code><br>
            <strong>Email:</strong> <code>${result.email}</code><br>
            <strong>Role:</strong> <code>${result.role}</code><br>
            <strong>Expires:</strong> <code>${expiryDate.toLocaleString()}</code>
        </div>
        <div style="margin-top:12px; padding:8px; background:white; border-radius:4px;">
            <strong>⚠️ Important:</strong> Save these credentials now. The password cannot be retrieved later.
        </div>
    `;
}

// Reset for Another Creation
function createAnother() {
    hideSection('result-section');
    hideSection('create-user-section');
    state.selectedSite = null;

    // Re-scan to refresh the list
    scanWordPress();
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();

    document.getElementById('scan-btn').addEventListener('click', scanWordPress);
    document.getElementById('create-btn').addEventListener('click', createUser);
    document.getElementById('create-another-btn').addEventListener('click', createAnother);

    // Refresh health every 30 seconds
    setInterval(checkHealth, 30000);
});
