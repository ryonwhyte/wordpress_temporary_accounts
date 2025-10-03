#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Cpanel::JSON();
use CGI();

run() unless caller();

sub run {
    my $cgi = CGI->new();
    my $request_method = $ENV{REQUEST_METHOD} || 'GET';

    # Get authenticated user
    my $cpanel_user = $ENV{REMOTE_USER} || '';
    unless ($cpanel_user) {
        if ($request_method eq 'POST') {
            print_json_error('not_authenticated', 'Authentication required');
        } else {
            print_html_error('Not Authenticated', 'You must be logged into cPanel.');
        }
        exit;
    }

    # Handle POST requests (API calls)
    if ($request_method eq 'POST') {
        handle_api_request($cgi, $cpanel_user);
    } else {
        # Handle GET requests (UI rendering)
        render_ui($cpanel_user);
    }

    exit;
}

###############################################################################
# Logging and Audit Trail
###############################################################################

sub write_audit_log {
    my ($cpanel_user, $action, $details, $result) = @_;

    my $log_dir = '/var/log/wp_temp_accounts';
    my $log_file = "$log_dir/cpanel.log";

    # Ensure log directory exists
    unless (-d $log_dir) {
        mkdir($log_dir, 0750) or return;
        chown 0, 0, $log_dir;
    }

    # Sanitize inputs for logging
    $cpanel_user = sanitize_log_input($cpanel_user);
    $action = sanitize_log_input($action);
    $details = sanitize_log_input($details);
    $result = sanitize_log_input($result);

    # Format: timestamp | user | action | details | result | remote_ip
    my $timestamp = scalar localtime(time());
    my $remote_ip = $ENV{REMOTE_ADDR} || 'unknown';
    my $log_entry = sprintf("[%s] %s | %s | %s | %s | %s\n",
        $timestamp, $cpanel_user, $action, $details, $result, $remote_ip);

    # Write to log file
    if (open my $fh, '>>', $log_file) {
        print $fh $log_entry;
        close $fh;
        chmod 0640, $log_file;
    }
}

###############################################################################
# Input Validation
###############################################################################

sub validate_username {
    my ($username) = @_;
    return 0 unless defined $username;
    return 0 if length($username) < 3 || length($username) > 60;
    return $username =~ /^[A-Za-z0-9._-]+$/;
}

sub validate_email {
    my ($email) = @_;
    return 0 unless defined $email;
    return 0 if length($email) < 5 || length($email) > 254;
    return $email =~ /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
}

sub validate_days {
    my ($days) = @_;
    return 0 unless defined $days;
    # Accept decimal values (e.g., 0.0208 for 30 minutes)
    return 0 unless $days =~ /^\d+\.?\d*$/;
    return $days >= 0.0208 && $days <= 365;  # 30 minutes to 1 year max
}

sub validate_site_path {
    my ($path, $cpanel_user) = @_;
    return 0 unless defined $path && defined $cpanel_user;
    return 0 if $path =~ /\.\./;  # Prevent directory traversal
    return 0 unless -d $path;

    my $homedir = (getpwnam($cpanel_user))[7];
    return 0 unless $homedir;
    return $path =~ /^\Q$homedir\E\//;
}

sub sanitize_log_input {
    my ($input) = @_;
    return '' unless defined $input;
    $input =~ s/[^\x20-\x7E]//g;  # Remove non-printable chars
    return substr($input, 0, 200);  # Limit length
}

###############################################################################
# API Request Handler
###############################################################################

sub handle_api_request {
    my ($cgi, $cpanel_user) = @_;

    # Read request body with size limit
    my $body = '';

    # Check if CGI.pm already read the body
    my $postdata = $cgi->param('POSTDATA');
    if (defined $postdata && $postdata ne '') {
        $body = $postdata;
    } else {
        # Read from STDIN directly
        my $content_length = $ENV{CONTENT_LENGTH} || 0;
        if ($content_length > 0) {
            read(STDIN, $body, $content_length);
        }
    }

    # Handle empty body
    unless ($body && $body ne '') {
        print_json_error('invalid_json', 'Empty request body');
        return;
    }

    my $request = eval { Cpanel::JSON::Load($body) };
    if ($@) {
        print_json_error('invalid_json', "Invalid JSON: $@");
        return;
    }

    my $action = $request->{action} || '';
    my $payload = $request->{payload} || {};

    # Route to appropriate handler
    if ($action eq 'health') {
        print_json_success({ status => 'ok', user => $cpanel_user });
    }
    elsif ($action eq 'scan_wordpress') {
        my $force_scan = $payload->{force_scan} || 0;
        my $sites = scan_wordpress($cpanel_user, $force_scan);
        print_json_success($sites);
    }
    elsif ($action eq 'load_cached_wordpress') {
        my $cached = load_cached_wordpress_scan($cpanel_user);
        print_json_success($cached);
    }
    elsif ($action eq 'create_temp_user') {
        create_temp_user($cpanel_user, $payload);
    }
    elsif ($action eq 'list_temp_users') {
        my $users = list_temp_users($cpanel_user, $payload->{site_path});
        print_json_success($users);
    }
    elsif ($action eq 'delete_temp_user') {
        delete_temp_user($cpanel_user, $payload);
    }
    elsif ($action eq 'list_all_temp_users') {
        my $all_users = list_all_temp_users($cpanel_user);
        print_json_success($all_users);
    }
    else {
        print_json_error('unknown_action', "Unknown action: $action");
    }
}

###############################################################################
# UI Rendering
###############################################################################

sub render_ui {
    my ($cpanel_user) = @_;

    print "Content-type: text/html; charset=utf-8\r\n\r\n";


    print <<'ENDHTML';
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Temporary Accounts</title>
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
</head>
<body>

<style type="text/css">
    /* Plugin-specific styling */
    .wp-temp-container { max-width: 100%; }
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 3px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-ok { background: #48bb78; color: white; }
    .status-error { background: #f56565; color: white; }
    .wp-card {
        background: #fff;
        padding: 20px;
        border-radius: 4px;
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .wp-card h2 {
        color: #2d3748;
        font-size: 18px;
        margin-bottom: 15px;
        font-weight: 600;
        padding-bottom: 10px;
        border-bottom: 1px solid #e2e8f0;
    }
    #loading {
        display: none;
        padding: 20px;
        text-align: center;
        background: #f7fafc;
        border-radius: 4px;
        margin: 20px 0;
        font-weight: 600;
        color: #1d8cf8;
    }
    #error-message {
        display: none;
        background: #fff5f5;
        color: #c53030;
        padding: 16px;
        border-radius: 4px;
        margin-bottom: 20px;
        border-left: 4px solid #f56565;
        font-weight: 500;
    }
    /* Password Modal */
    #password-modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.6);
        z-index: 10000;
        align-items: center;
        justify-content: center;
    }
    #password-modal.show {
        display: flex;
    }
    .modal-content {
        background: white;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        max-width: 500px;
        width: 90%;
    }
    .modal-header {
        font-size: 24px;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    .modal-header i {
        color: #48bb78;
        margin-right: 10px;
    }
    .password-display {
        background: #f7fafc;
        padding: 15px;
        border-radius: 4px;
        border: 2px solid #4299e1;
        margin: 15px 0;
        font-family: monospace;
        font-size: 16px;
        word-break: break-all;
        position: relative;
    }
    .copy-btn {
        background: #4299e1;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        margin-top: 10px;
        transition: all 0.2s;
    }
    .copy-btn:hover {
        background: #3182ce;
    }
    .copy-btn.copied {
        background: #48bb78;
    }
    .modal-footer {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #e2e8f0;
    }
    .modal-info {
        background: #fff5f5;
        padding: 12px;
        border-radius: 4px;
        border-left: 4px solid #f56565;
        margin: 15px 0;
        font-size: 13px;
        color: #c53030;
    }
    /* Tab Navigation */
    .tab-navigation {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
        border-bottom: 2px solid #e2e8f0;
    }
    .tab-button {
        background: none;
        border: none;
        padding: 12px 24px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        color: #718096;
        border-bottom: 3px solid transparent;
        transition: all 0.2s;
        margin-bottom: -2px;
    }
    .tab-button:hover {
        color: #4299e1;
        background: #f7fafc;
    }
    .tab-button.active {
        color: #4299e1;
        border-bottom-color: #4299e1;
    }
    .tab-content {
        display: none;
    }
    .tab-content.active {
        display: block;
    }
    .form-group {
        margin-bottom: 15px;
    }
    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: 600;
        color: #4a5568;
    }
    .form-control {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        font-size: 14px;
    }
    .btn {
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .btn-primary {
        background: #1d8cf8;
        color: white;
    }
    .btn-primary:hover {
        background: #0d7dea;
    }
    .btn-success {
        background: #48bb78;
        color: white;
    }
    .btn-success:hover {
        background: #38a169;
    }
    .btn-danger {
        background: #f56565;
        color: white;
    }
    .btn-danger:hover {
        background: #e53e3e;
    }
    .btn-sm {
        padding: 5px 10px;
        font-size: 12px;
    }
    .table {
        width: 100%;
        border-collapse: collapse;
    }
    .table th {
        background: #f7fafc;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid #e2e8f0;
        font-weight: 600;
        color: #4a5568;
    }
    .table td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
    }
    .table-striped tbody tr:nth-child(even) {
        background: #f7fafc;
    }
</style>

<div class="wp-temp-container">
    <div class="section">
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 24px; color: #2d3748; margin-bottom: 10px;">WordPress Temporary Accounts</h1>
            <span id="health-status" class="status-badge status-ok">System: OK</span>
        </div>

        <div id="error-message"></div>
        <div id="loading">Loading...</div>

        <!-- Tab Navigation -->
        <div class="tab-navigation">
            <button class="tab-button active" data-tab="create-tab">
                <i class="fa fa-plus-circle"></i> Create User
            </button>
            <button class="tab-button" data-tab="manage-tab">
                <i class="fa fa-users"></i> Manage All Users
            </button>
        </div>

        <!-- Password Modal -->
        <div id="password-modal">
            <div class="modal-content">
                <div class="modal-header">
                    <i class="fa fa-check-circle"></i>
                    User Created Successfully!
                </div>
                <div>
                    <strong>Username:</strong>
                    <div id="modal-username" style="font-family: monospace; margin: 5px 0 15px 0;"></div>

                    <strong>Password:</strong>
                    <div class="password-display" id="modal-password"></div>

                    <button id="copy-password-btn" class="copy-btn">
                        <i class="fa fa-copy"></i> Copy Password
                    </button>

                    <div class="modal-info">
                        <i class="fa fa-exclamation-triangle"></i>
                        Save this password now! It cannot be retrieved later.
                    </div>

                    <div style="margin-top: 10px; color: #718096; font-size: 13px;">
                        <strong>Expires:</strong> <span id="modal-expires"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="close-modal-btn" class="btn btn-success" style="width: 100%;">
                        I've Saved the Password
                    </button>
                </div>
            </div>
        </div>

        <!-- Tab: Create User -->
        <div id="create-tab" class="tab-content active">
            <!-- Step 1: Select WordPress Installation -->
        <div class="wp-card">
            <h2>1. Select WordPress Installation</h2>
            <div class="form-group">
                <label for="wp-site">WordPress Site:</label>
                <select id="wp-site" class="form-control">
                    <option value="">Loading WordPress sites...</option>
                </select>
            </div>
            <div class="form-group">
                <button id="scan-btn" class="btn btn-primary">
                    <i class="fa fa-refresh"></i> Scan for WordPress
                </button>
                <span id="cache-status" style="margin-left: 15px; color: #718096; font-size: 13px;"></span>
            </div>
        </div>

        <!-- Step 2: Create Temporary User -->
        <div class="wp-card" id="create-user-section" style="display:none;">
            <h2>2. Create Temporary User</h2>
            <div class="form-group">
                <label for="wp-temp-username">Username:</label>
                <input type="text" id="wp-temp-username" class="form-control" placeholder="temp_admin_123">
            </div>
            <div class="form-group">
                <label for="wp-temp-email">Email:</label>
                <input type="email" id="wp-temp-email" class="form-control" placeholder="temp@example.com">
            </div>
            <div class="form-group">
                <label for="wp-temp-expiration">Expiration:</label>
                <select id="wp-temp-expiration" class="form-control">
                    <option value="0.0208">30 Minutes</option>
                    <option value="0.0417">1 Hour</option>
                    <option value="0.0833">2 Hours</option>
                    <option value="0.25">6 Hours</option>
                    <option value="0.5">12 Hours</option>
                    <option value="1">1 Day</option>
                    <option value="7" selected>7 Days</option>
                    <option value="14">14 Days</option>
                    <option value="30">30 Days</option>
                </select>
            </div>
            <button id="create-btn" class="btn btn-success">Create Temporary User</button>
        </div>
        </div><!-- End create-tab -->

        <!-- Tab: Manage All Users -->
        <div id="manage-tab" class="tab-content">
            <div class="wp-card">
                <h2>
                    <i class="fa fa-users"></i> All Temporary Users
                    <button id="refresh-all-users-btn" class="btn btn-primary btn-sm" style="float: right; margin-top: -5px;">
                        <i class="fa fa-refresh"></i> Refresh
                    </button>
                </h2>
                <div id="all-users-filter" style="margin-bottom: 15px;">
                    <input type="text" id="filter-input" class="form-control" placeholder="Filter by site, username, or email..." style="max-width: 400px;">
                </div>
                <div id="all-users-container">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>WordPress Site</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Expires</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="all-users-table">
                            <tr><td colspan="5" style="text-align: center; padding: 20px; color: #718096;">
                                <i class="fa fa-spinner fa-spin"></i> Loading all temporary users...
                            </td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div><!-- End manage-tab -->
    </div>
</div>

<script>
    // State
    let state = { selectedSite: null };

    // API Communication
    async function callAPI(action, payload = {}) {
        showLoading();
        try {
            const response = await fetch(window.location.pathname, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, payload })
            });
            const data = await response.json();
            hideLoading();
            if (!data.ok) throw new Error(data.error?.message || 'Unknown error');
            return data.data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    // UI Helpers
    function showLoading() { document.getElementById('loading').style.display = 'block'; }
    function hideLoading() { document.getElementById('loading').style.display = 'none'; }
    function showError(msg) {
        const el = document.getElementById('error-message');
        el.textContent = msg;
        el.style.display = 'block';
        setTimeout(() => el.style.display = 'none', 5000);
    }

    // Load cached WordPress sites
    async function loadCachedWordPress() {
        try {
            const sites = await callAPI('load_cached_wordpress', {});
            if (sites && sites.length > 0) {
                populateWordPressSites(sites);
                updateCacheStatus('Loaded from cache (click Scan to refresh)');
                return true;
            }
        } catch (error) {
            console.log('No cached data available');
        }
        return false;
    }

    // Scan for WordPress (force refresh)
    async function scanWordPress() {
        const sites = await callAPI('scan_wordpress', { force_scan: 1 });
        populateWordPressSites(sites);
        updateCacheStatus(`Scanned ${sites.length} site(s) - cached for 1 hour`);
    }

    // Populate WordPress sites dropdown
    function populateWordPressSites(sites) {
        const select = document.getElementById('wp-site');
        select.innerHTML = '<option value="">-- Select a site --</option>';

        if (sites.length === 0) {
            select.innerHTML = '<option value="">No WordPress installations found</option>';
            select.disabled = true;
        } else {
            sites.forEach(site => {
                const opt = document.createElement('option');
                opt.value = site.path;
                opt.textContent = `${site.domain} (${site.path})`;
                select.appendChild(opt);
            });
            select.disabled = false;
        }
    }

    // Update cache status message
    function updateCacheStatus(message) {
        const statusEl = document.getElementById('cache-status');
        if (statusEl) {
            statusEl.textContent = message;
        }
    }

    // Stub for loadUsers - no longer needed with new tab-based UI
    // Just refresh the all-users tab if it's active
    async function loadUsers() {
        // Refresh all users table instead
        if (document.getElementById('manage-tab').classList.contains('active')) {
            loadAllTempUsers();
        }
    }

    // Create User
    async function createUser() {
        const usernameEl = document.getElementById('wp-temp-username');
        const emailEl = document.getElementById('wp-temp-email');
        const expirationEl = document.getElementById('wp-temp-expiration');

        if (!usernameEl || !emailEl || !expirationEl) {
            showError('Form fields not found');
            return;
        }

        // Check if value property exists
        if (usernameEl.value === undefined || emailEl.value === undefined || expirationEl.value === undefined) {
            showError('Form fields not properly initialized');
            return;
        }

        const username = (usernameEl.value || '').trim();
        const email = (emailEl.value || '').trim();
        const days = parseFloat(expirationEl.value || '7');

        if (!username || !email) {
            showError('Username and email are required');
            return;
        }

        if (username.length < 3 || username.length > 60) {
            showError('Username must be between 3 and 60 characters');
            return;
        }

        if (!/^[A-Za-z0-9._-]+$/.test(username)) {
            showError('Username can only contain letters, numbers, dots, underscores, and hyphens');
            return;
        }

        if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email)) {
            showError('Please enter a valid email address');
            return;
        }

        const result = await callAPI('create_temp_user', {
            site_path: state.selectedSite,
            username,
            email,
            days: days
        });

        // Show password to user in modal
        if (result && result.password) {
            showPasswordModal(result);
        }

        document.getElementById('wp-temp-username').value = '';
        document.getElementById('wp-temp-email').value = '';
    }

    // Show Password Modal
    function showPasswordModal(result) {
        document.getElementById('modal-username').textContent = result.username;
        document.getElementById('modal-password').textContent = result.password;
        document.getElementById('modal-expires').textContent = result.expires || 'N/A';
        document.getElementById('password-modal').classList.add('show');

        // Store password for copy function
        window.currentPassword = result.password;
    }

    // Copy Password to Clipboard
    document.getElementById('copy-password-btn').addEventListener('click', function() {
        const password = window.currentPassword;
        if (!password) return;

        // Use Clipboard API if available, fallback to textarea method
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(password).then(() => {
                showCopySuccess();
            }).catch(() => {
                fallbackCopy(password);
            });
        } else {
            fallbackCopy(password);
        }
    });

    function fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopySuccess();
        } catch (err) {
            showError('Failed to copy password');
        }
        document.body.removeChild(textarea);
    }

    function showCopySuccess() {
        const btn = document.getElementById('copy-password-btn');
        btn.innerHTML = '<i class="fa fa-check"></i> Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = '<i class="fa fa-copy"></i> Copy Password';
            btn.classList.remove('copied');
        }, 2000);
    }

    // Close Modal
    document.getElementById('close-modal-btn').addEventListener('click', function() {
        document.getElementById('password-modal').classList.remove('show');
        window.currentPassword = null;
        loadUsers();  // Refresh the users table
    });


    // Delete User
    async function deleteUser(username) {
        if (!confirm(`Delete user ${username}?`)) return;
        await callAPI('delete_temp_user', {
            site_path: state.selectedSite,
            username
        });
        loadUsers();
    }

    // Delete User from All Users Table
    async function deleteUserFromAll(sitePath, username) {
        if (!confirm(`Delete user ${username} from ${sitePath}?`)) return;
        await callAPI('delete_temp_user', {
            site_path: sitePath,
            username
        });
        loadAllTempUsers();  // Refresh all users table
        if (state.selectedSite === sitePath) {
            loadUsers();  // Also refresh site-specific table if viewing that site
        }
    }

    // Load All Temporary Users
    let allUsersData = [];  // Store for filtering

    async function loadAllTempUsers() {
        try {
            const users = await callAPI('list_all_temp_users');
            allUsersData = users;
            displayAllUsers(users);
        } catch (error) {
            console.error('Failed to load all temp users:', error);
            const tbody = document.getElementById('all-users-table');
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #e53e3e;">Failed to load users</td></tr>';
        }
    }

    function displayAllUsers(users) {
        const tbody = document.getElementById('all-users-table');

        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #718096;">No temporary users found</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => `
            <tr>
                <td title="${escapeHtml(u.site_path)}">${escapeHtml(u.site_domain)}</td>
                <td>${escapeHtml(u.username)}</td>
                <td>${escapeHtml(u.email)}</td>
                <td>${escapeHtml(u.expires)}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="deleteUserFromAll('${escapeHtml(u.site_path)}', '${escapeHtml(u.username)}')">
                        <i class="fa fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `).join('');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Filter All Users Table
    document.getElementById('filter-input').addEventListener('input', function() {
        const filterText = this.value.toLowerCase();
        if (!filterText) {
            displayAllUsers(allUsersData);
            return;
        }

        const filtered = allUsersData.filter(u => {
            return (
                u.site_domain.toLowerCase().includes(filterText) ||
                u.site_path.toLowerCase().includes(filterText) ||
                u.username.toLowerCase().includes(filterText) ||
                u.email.toLowerCase().includes(filterText)
            );
        });

        displayAllUsers(filtered);
    });

    // Refresh All Users Button
    document.getElementById('refresh-all-users-btn').addEventListener('click', loadAllTempUsers);

    // Tab Switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // Update button states
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Update tab content visibility
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');

            // Load data for manage tab when switching to it
            if (targetTab === 'manage-tab') {
                loadAllTempUsers();
            }
        });
    });

    // Event Listeners
    document.getElementById('scan-btn').addEventListener('click', scanWordPress);
    document.getElementById('wp-site').addEventListener('change', function() {
        const selectedSite = this.value;
        if (selectedSite) {
            state.selectedSite = selectedSite;
            // Auto-show create form when site is selected
            document.getElementById('create-user-section').style.display = 'block';
        } else {
            document.getElementById('create-user-section').style.display = 'none';
        }
    });
    document.getElementById('create-btn').addEventListener('click', createUser);

    // Initialize
    loadCachedWordPress();
    callAPI('health').catch(() => {
        document.getElementById('health-status').textContent = 'System: Error';
        document.getElementById('health-status').className = 'status-badge status-error';
    });
</script>

</body>
</html>
ENDHTML
}

###############################################################################
# Core Functions
###############################################################################

###############################################################################
# WordPress Scan Caching
###############################################################################

sub get_cache_dir {
    my $cache_dir = '/var/cache/wp_temp_accounts';
    unless (-d $cache_dir) {
        mkdir($cache_dir, 0750) or return undef;
    }
    return $cache_dir;
}

sub get_cache_file {
    my ($account) = @_;
    return undef unless $account;

    my $cache_dir = get_cache_dir();
    return undef unless $cache_dir;

    # Sanitize account name for filename
    $account =~ s/[^a-zA-Z0-9_-]/_/g;
    return "$cache_dir/wp_scan_${account}.json";
}

sub save_cached_wordpress_scan {
    my ($account, $sites) = @_;
    return unless $account && $sites;

    my $cache_file = get_cache_file($account);
    return unless $cache_file;

    my $data = {
        account => $account,
        timestamp => time(),
        sites => $sites
    };

    if (open my $fh, '>', $cache_file) {
        print $fh Cpanel::JSON::Dump($data);
        close $fh;
        chmod 0640, $cache_file;

        write_audit_log('CACHE_WORDPRESS_SCAN', "account=$account sites=" . scalar(@$sites), 'success');
    }
}

sub load_cached_wordpress_scan {
    my ($account) = @_;
    return undef unless $account;

    my $cache_file = get_cache_file($account);
    return undef unless $cache_file && -f $cache_file;

    # Check cache age (valid for 1 hour = 3600 seconds)
    my $max_age = 3600;
    my $cache_mtime = (stat($cache_file))[9];
    if (time() - $cache_mtime > $max_age) {
        # Cache expired
        unlink $cache_file;
        return undef;
    }

    # Load cached data
    if (open my $fh, '<', $cache_file) {
        local $/;
        my $json = <$fh>;
        close $fh;

        my $data = eval { Cpanel::JSON::Load($json) };
        if ($data && $data->{sites}) {
            return $data->{sites};
        }
    }

    return undef;
}

sub scan_wordpress {
    my ($cpanel_user, $force_scan) = @_;

    # Try to load cached results if not forcing a scan
    unless ($force_scan) {
        my $cached = load_cached_wordpress_scan($cpanel_user);
        if ($cached && @$cached) {
            return $cached;
        }
    }

    # Perform actual scan
    my $homedir = (getpwnam($cpanel_user))[7];
    return [] unless $homedir && -d $homedir;

    my @sites;
    my @search_roots = (
        "$homedir/public_html",
        "$homedir/www",
        glob("$homedir/domains/*/public_html")
    );

    # Recursively search for wp-config.php files
    foreach my $root (@search_roots) {
        next unless -d $root;
        find_wordpress_recursive($root, $homedir, \@sites);
    }

    # Cache the results
    save_cached_wordpress_scan($cpanel_user, \@sites);

    return \@sites;
}

sub find_wordpress_recursive {
    my ($dir, $homedir, $sites_ref) = @_;

    # Security: Don't scan too deep (max 5 levels)
    my $depth = ($dir =~ tr/\///);
    my $root_depth = ($homedir =~ tr/\///);
    return if ($depth - $root_depth) > 5;

    # Check current directory for wp-config.php
    my $wp_config = "$dir/wp-config.php";
    if (-f $wp_config) {
        # Found WordPress installation
        my $domain = extract_domain_from_path($dir, $homedir);

        # Get site URL from wp-config if possible
        my $site_url = extract_site_url($wp_config) || $domain;

        push @$sites_ref, {
            path => $dir,
            domain => $site_url,
            wp_config => $wp_config
        };

        # Don't scan subdirectories if we found WordPress here
        # (WordPress installations shouldn't be nested)
        return;
    }

    # Scan subdirectories
    opendir(my $dh, $dir) or return;
    my @subdirs = grep {
        $_ ne '.' && $_ ne '..' &&
        -d "$dir/$_" &&
        $_ !~ /^\./ &&  # Skip hidden directories
        $_ ne 'wp-admin' &&  # Skip WP directories
        $_ ne 'wp-content' &&
        $_ ne 'wp-includes'
    } readdir($dh);
    closedir($dh);

    foreach my $subdir (@subdirs) {
        find_wordpress_recursive("$dir/$subdir", $homedir, $sites_ref);
    }
}

sub extract_domain_from_path {
    my ($path, $homedir) = @_;

    # Remove homedir prefix
    my $relative = $path;
    $relative =~ s/^\Q$homedir\E\/?//;

    # Extract domain from common patterns
    if ($relative =~ m|^domains/([^/]+)|) {
        return $1;  # domains/example.com/public_html
    }
    elsif ($relative =~ m|^public_html/([^/]+)|) {
        return $1;  # public_html/subfolder
    }
    elsif ($relative eq 'public_html' || $relative eq 'www') {
        return 'Main Site (public_html)';
    }

    return $relative || 'Unknown';
}

sub extract_site_url {
    my ($wp_config) = @_;

    # Try to read WP_SITEURL or WP_HOME from wp-config.php
    if (open my $fh, '<', $wp_config) {
        while (my $line = <$fh>) {
            if ($line =~ /define\s*\(\s*['"](?:WP_SITEURL|WP_HOME)['"]\s*,\s*['"]([^'"]+)['"]/) {
                close $fh;
                my $url = $1;
                $url =~ s|^https?://||;
                $url =~ s|/$||;
                return $url;
            }
        }
        close $fh;
    }

    return undef;
}

sub create_temp_user {
    my ($cpanel_user, $payload) = @_;

    my $site_path = $payload->{site_path} || '';
    my $username = $payload->{username} || '';
    my $email = $payload->{email} || '';
    my $days = $payload->{days} || 7;

    # Validate presence
    unless ($site_path && $username && $email) {
        print_json_error('missing_params', 'Missing required parameters');
        return;
    }

    # Validate username format
    unless (validate_username($username)) {
        print_json_error('invalid_username', 'Username must be 3-60 characters, alphanumeric with ._- only');
        return;
    }

    # Validate email format
    unless (validate_email($email)) {
        print_json_error('invalid_email', 'Invalid email address format');
        return;
    }

    # Validate days
    unless (validate_days($days)) {
        print_json_error('invalid_days', 'Days must be between 1 and 365');
        return;
    }

    # Validate site_path is under the user's homedir
    unless (validate_site_path($site_path, $cpanel_user)) {
        print_json_error('invalid_path', 'Invalid site path - must be under your home directory');
        return;
    }

    # Generate password
    my $password = generate_password();

    # Create user with WP-CLI
    my $expires = time() + ($days * 86400);
    my $cmd = qq{sudo -u $cpanel_user wp user create "$username" "$email" --role=administrator --user_pass="$password" --path="$site_path" 2>&1};
    my $output = `$cmd`;

    if ($? != 0) {
        write_audit_log($cpanel_user, 'CREATE_USER_FAILED', "user=$username site=$site_path", "error: $output");
        print_json_error('wp_cli_error', "Failed to create user: $output");
        return;
    }

    # Add expiration meta
    `sudo -u $cpanel_user wp user meta update "$username" wp_temp_user 1 --path="$site_path"`;
    `sudo -u $cpanel_user wp user meta update "$username" wp_temp_expires $expires --path="$site_path"`;

    # Get site domain for registry
    my $site_domain = extract_domain_from_site_path($site_path, $cpanel_user);

    # Add to registry
    add_to_registry({
        cpanel_account => $cpanel_user,
        site_domain => $site_domain,
        site_path => $site_path,
        username => $username,
        email => $email,
        created => time(),
        expires => $expires
    });

    # Log successful creation
    write_audit_log($cpanel_user, 'CREATE_USER_SUCCESS', "user=$username site=$site_path days=$days", "success");

    print_json_success({
        username => $username,
        email => $email,
        password => $password,
        expires => scalar localtime($expires)
    });
}

sub list_temp_users {
    my ($cpanel_user, $site_path) = @_;
    return [] unless $site_path && -d $site_path;

    # Validate path
    my $homedir = (getpwnam($cpanel_user))[7];
    return [] unless $site_path =~ /^\Q$homedir\E\//;

    my @users;
    my $cmd = qq{sudo -u $cpanel_user wp user list --role=administrator --path="$site_path" --format=json 2>&1};
    my $output = `$cmd`;

    if ($? == 0) {
        my $all_users = eval { Cpanel::JSON::Load($output) } || [];

        foreach my $user (@$all_users) {
            my $username = $user->{user_login};
            my $is_temp = `sudo -u $cpanel_user wp user meta get "$username" wp_temp_user --path="$site_path" 2>&1`;
            chomp $is_temp;

            if ($is_temp eq '1') {
                my $expires = `sudo -u $cpanel_user wp user meta get "$username" wp_temp_expires --path="$site_path" 2>&1`;
                chomp $expires;

                push @users, {
                    username => $username,
                    email => $user->{user_email},
                    expires => $expires ? scalar localtime($expires) : 'Never'
                };
            }
        }
    }

    return \@users;
}

sub delete_temp_user {
    my ($cpanel_user, $payload) = @_;

    my $site_path = $payload->{site_path} || '';
    my $username = $payload->{username} || '';

    unless ($site_path && $username) {
        print_json_error('missing_params', 'Missing required parameters');
        return;
    }

    # Validate path
    my $homedir = (getpwnam($cpanel_user))[7];
    unless ($site_path =~ /^\Q$homedir\E\//) {
        print_json_error('invalid_path', 'Invalid site path');
        return;
    }

    my $cmd = qq{sudo -u $cpanel_user wp user delete "$username" --yes --path="$site_path" 2>&1};
    my $output = `$cmd`;

    if ($? != 0) {
        write_audit_log($cpanel_user, 'DELETE_USER_FAILED', "user=$username site=$site_path", "error: $output");
        print_json_error('wp_cli_error', "Failed to delete user: $output");
        return;
    }

    # Remove from registry
    remove_from_registry($cpanel_user, $site_path, $username);

    # Log successful deletion
    write_audit_log($cpanel_user, 'DELETE_USER_SUCCESS', "user=$username site=$site_path", "success");

    print_json_success({ deleted => $username });
}

sub list_all_temp_users {
    my ($cpanel_user) = @_;

    # Get user's temp users from registry - instant!
    my $users = get_all_temp_users_from_registry($cpanel_user);

    # Format expires timestamp as readable date
    foreach my $user (@$users) {
        if ($user->{expires} && $user->{expires} =~ /^\d+$/) {
            $user->{expires} = scalar localtime($user->{expires});
        }
    }

    return $users;
}

###############################################################################
# Registry Management
###############################################################################

sub get_registry_path {
    return '/var/cache/wp_temp_accounts/registry.json';
}

sub load_registry {
    my $registry_file = get_registry_path();

    # Create empty registry if doesn't exist
    unless (-f $registry_file) {
        return { users => [] };
    }

    # Read registry file
    if (open my $fh, '<', $registry_file) {
        local $/;
        my $json = <$fh>;
        close $fh;

        my $data = eval { Cpanel::JSON::Load($json) };
        if ($@) {
            write_audit_log('', 'REGISTRY_LOAD_ERROR', "error=$@", 'failed');
            return { users => [] };
        }

        return $data;
    }

    return { users => [] };
}

sub save_registry {
    my ($data) = @_;

    my $registry_file = get_registry_path();
    my $registry_dir = '/var/cache/wp_temp_accounts';

    # Ensure directory exists
    unless (-d $registry_dir) {
        mkdir($registry_dir, 0750) or return 0;
        chown 0, 0, $registry_dir;
    }

    # Write with file locking
    if (open my $fh, '>', $registry_file) {
        flock($fh, 2);  # LOCK_EX
        print $fh Cpanel::JSON::Dump($data);
        flock($fh, 8);  # LOCK_UN
        close $fh;

        # Set restrictive permissions
        chmod 0600, $registry_file;
        chown 0, 0, $registry_file;

        return 1;
    }

    return 0;
}

sub add_to_registry {
    my ($user_data) = @_;

    my $registry = load_registry();
    push @{$registry->{users}}, $user_data;

    return save_registry($registry);
}

sub remove_from_registry {
    my ($cpanel_user, $site_path, $username) = @_;

    my $registry = load_registry();
    my @filtered = grep {
        !($_->{cpanel_account} eq $cpanel_user &&
          $_->{site_path} eq $site_path &&
          $_->{username} eq $username)
    } @{$registry->{users}};

    $registry->{users} = \@filtered;

    return save_registry($registry);
}

sub get_all_temp_users_from_registry {
    my ($cpanel_user) = @_;
    my $registry = load_registry();

    # Filter to only this cPanel user's sites
    my @filtered = grep { $_->{cpanel_account} eq $cpanel_user } @{$registry->{users}};

    return \@filtered;
}

sub extract_domain_from_site_path {
    my ($site_path, $cpanel_user) = @_;

    my $homedir = (getpwnam($cpanel_user))[7];
    return extract_domain_from_path($site_path, $homedir);
}

###############################################################################
# Helpers
###############################################################################

sub generate_password {
    my @chars = ('a'..'z', 'A'..'Z', '0'..'9', '!@#$%^&*');
    my $password = '';
    $password .= $chars[int(rand(@chars))] for 1..16;
    return $password;
}

sub print_json_success {
    my ($data) = @_;
    print "Content-Type: application/json\r\n\r\n";
    print Cpanel::JSON::Dump({ ok => Cpanel::JSON::true, data => $data });
}

sub print_json_error {
    my ($code, $message) = @_;
    print "Content-Type: application/json\r\n\r\n";
    print Cpanel::JSON::Dump({
        ok => Cpanel::JSON::false,
        error => { code => $code, message => $message }
    });
}

sub print_html_error {
    my ($title, $message) = @_;
    print "Content-type: text/html; charset=utf-8\n\n";
    print "<h1>$title</h1>\n<p>$message</p>\n";
}

1;
