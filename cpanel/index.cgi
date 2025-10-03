#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Cpanel::JSON();
use Cpanel::Template();
use Cpanel::LiveAPI();
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

    # Set up proper cPanel template variables
    my %template_vars = (
        'cpanel_user' => $cpanel_user,
        'plugin_path' => 'wp_temp_accounts',
    );

    # Output headers
    print "Content-type: text/html\r\n\r\n";

    # Process the template using cPanel's Template module
    # The template path is relative to the theme directory
    eval {
        Cpanel::Template::process_template(
            'cpanel',
            {
                'template_file' => 'wp_temp_accounts/index.tmpl',
                'print'         => 1,
                %template_vars
            }
        );
    };

    if ($@) {
        # If template fails, show a simple error with the actual error details
        print qq{
            <html>
            <head><title>WordPress Temporary Accounts - Error</title></head>
            <body>
                <h1>Template Processing Error</h1>
                <p>Unable to load the cPanel template.</p>
                <pre>$@</pre>
                <p>Template path should be: /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.tmpl</p>
                <p>Current user: $cpanel_user</p>
            </body>
            </html>
        };
    }

    return;
}

sub print_html_interface_disabled {
    my ($cpanel_user) = @_;

    # Output the complete HTML interface directly
    print <<'HTML_START';
<!DOCTYPE html>
<html>
<head>
    <title>WordPress Temporary Accounts</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style type="text/css">
        /* Plugin-specific styling */
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
        .wp-temp-container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { margin: 0 0 10px 0; color: #333; font-size: 24px; }
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

        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .tab-button {
            padding: 10px 20px;
            background: #e2e8f0;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }
        .tab-button:hover { background: #cbd5e0; }
        .tab-button.active {
            background: #4299e1;
            color: white;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .wp-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .wp-card h2 {
            color: #2d3748;
            font-size: 18px;
            margin: 0 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
        }

        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #4a5568;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #cbd5e0;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66,153,225,0.1);
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #4299e1;
            color: white;
        }
        .btn-primary:hover { background: #3182ce; }
        .btn-danger {
            background: #f56565;
            color: white;
        }
        .btn-danger:hover { background: #e53e3e; }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        tr:hover { background: #f7fafc; }

        #loading {
            display: none;
            padding: 20px;
            text-align: center;
            background: #fff;
            border-radius: 8px;
            margin: 20px 0;
        }
        #error-message {
            display: none;
            background: #fff5f5;
            color: #c53030;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #f56565;
        }

        /* Password Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.show { display: flex; }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            max-width: 500px;
            width: 90%;
        }
        .modal-header {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .password-display {
            background: #f7fafc;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 16px;
            margin: 15px 0;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="wp-temp-container">
        <div class="header">
            <h1>WordPress Temporary Accounts</h1>
            <p>User: <strong>
HTML_START
    print $cpanel_user;
    print <<'HTML_END';
</strong></p>
            <span id="health-status" class="status-badge status-ok">System: OK</span>
        </div>

        <div id="error-message"></div>
        <div id="loading">Loading...</div>

        <!-- Tab Navigation -->
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('create')">Create User</button>
            <button class="tab-button" onclick="showTab('manage')">Manage All Users</button>
        </div>

        <!-- Create User Tab -->
        <div id="create-tab" class="tab-content active">
            <div class="wp-card">
                <h2>1. Select WordPress Site</h2>
                <div class="form-group">
                    <button id="scan-btn" class="btn btn-primary" onclick="scanWordPress()">Scan for WordPress Sites</button>
                </div>
                <div class="form-group" id="site-select-group" style="display:none;">
                    <label for="wp-site">WordPress Site:</label>
                    <select id="wp-site" onchange="siteSelected()">
                        <option value="">-- Select a site --</option>
                    </select>
                </div>
            </div>

            <div class="wp-card" id="create-form" style="display:none;">
                <h2>2. Create Temporary User</h2>
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" placeholder="temp_admin_123">
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" placeholder="temp@example.com">
                </div>
                <div class="form-group">
                    <label for="days">Expiration (days):</label>
                    <input type="number" id="days" value="7" min="0.0208" max="365" step="0.0001">
                </div>
                <button class="btn btn-primary" onclick="createUser()">Create Temporary User</button>
            </div>
        </div>

        <!-- Manage Users Tab -->
        <div id="manage-tab" class="tab-content">
            <div class="wp-card">
                <h2>All Temporary Users</h2>
                <div class="form-group">
                    <input type="text" id="filter-input" placeholder="Filter users..." onkeyup="filterUsers()">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Site</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Expires</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="users-table">
                        <tr><td colspan="5">Click "Load All Users" to view temporary users</td></tr>
                    </tbody>
                </table>
                <button class="btn btn-primary" onclick="loadAllUsers()">Load All Users</button>
            </div>
        </div>
    </div>

    <!-- Password Modal -->
    <div id="password-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">User Created Successfully</div>
            <p>Username: <strong id="modal-username"></strong></p>
            <p>Password:</p>
            <div class="password-display" id="modal-password"></div>
            <button class="btn btn-primary" onclick="copyPassword()">Copy Password</button>
            <button class="btn" onclick="closeModal()">Close</button>
        </div>
    </div>

    <script>
        let selectedSite = null;
        let cpanelUser = '
HTML_END
    print $cpanel_user;
    print <<'HTML_SCRIPT';
';

        // Tab switching
        function showTab(tab) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            if (tab === 'create') {
                document.querySelector('.tab-button:nth-child(1)').classList.add('active');
                document.getElementById('create-tab').classList.add('active');
            } else {
                document.querySelector('.tab-button:nth-child(2)').classList.add('active');
                document.getElementById('manage-tab').classList.add('active');
                loadAllUsers();
            }
        }

        // API call helper
        async function callAPI(action, payload = {}) {
            const loading = document.getElementById('loading');
            loading.style.display = 'block';

            try {
                const response = await fetch(window.location.pathname, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, payload })
                });
                const data = await response.json();
                loading.style.display = 'none';

                if (!data.ok) {
                    throw new Error(data.error?.message || 'Unknown error');
                }
                return data.data;
            } catch (error) {
                loading.style.display = 'none';
                showError(error.message);
                throw error;
            }
        }

        function showError(msg) {
            const el = document.getElementById('error-message');
            el.textContent = msg;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 5000);
        }

        async function scanWordPress() {
            const sites = await callAPI('scan_wordpress', { force_scan: true });
            const select = document.getElementById('wp-site');
            select.innerHTML = '<option value="">-- Select a site --</option>';

            sites.forEach(site => {
                const opt = document.createElement('option');
                opt.value = site.path;
                opt.textContent = `${site.domain} (${site.path})`;
                select.appendChild(opt);
            });

            document.getElementById('site-select-group').style.display = 'block';
        }

        function siteSelected() {
            selectedSite = document.getElementById('wp-site').value;
            if (selectedSite) {
                document.getElementById('create-form').style.display = 'block';
            }
        }

        async function createUser() {
            const username = document.getElementById('username').value;
            const email = document.getElementById('email').value;
            const days = document.getElementById('days').value;

            if (!username || !email) {
                showError('Username and email are required');
                return;
            }

            const result = await callAPI('create_temp_user', {
                cpanel_user: cpanelUser,
                site_path: selectedSite,
                username,
                email,
                days: parseFloat(days)
            });

            // Show password modal
            document.getElementById('modal-username').textContent = result.username;
            document.getElementById('modal-password').textContent = result.password;
            document.getElementById('password-modal').classList.add('show');

            // Clear form
            document.getElementById('username').value = '';
            document.getElementById('email').value = '';
        }

        function copyPassword() {
            const password = document.getElementById('modal-password').textContent;
            navigator.clipboard.writeText(password);
            alert('Password copied to clipboard!');
        }

        function closeModal() {
            document.getElementById('password-modal').classList.remove('show');
        }

        async function loadAllUsers() {
            const users = await callAPI('list_all_temp_users');
            const tbody = document.getElementById('users-table');

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No temporary users found</td></tr>';
            } else {
                tbody.innerHTML = users.map(u => `
                    <tr>
                        <td>${u.site_domain}</td>
                        <td>${u.username}</td>
                        <td>${u.email}</td>
                        <td>${u.expires}</td>
                        <td><button class="btn btn-danger" onclick="deleteUser('${u.site_path}', '${u.username}')">Delete</button></td>
                    </tr>
                `).join('');
            }
        }

        async function deleteUser(sitePath, username) {
            if (!confirm(`Delete user ${username}?`)) return;

            await callAPI('delete_temp_user', {
                cpanel_user: cpanelUser,
                site_path: sitePath,
                username
            });

            loadAllUsers();
        }

        function filterUsers() {
            const filter = document.getElementById('filter-input').value.toLowerCase();
            const rows = document.querySelectorAll('#users-table tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        }

        // Check health on load
        callAPI('health').catch(() => {
            document.getElementById('health-status').textContent = 'System: Error';
            document.getElementById('health-status').className = 'status-badge status-error';
        });
    </script>
</body>
</html>
HTML_SCRIPT
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

