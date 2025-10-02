#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

#WHMADDON:wp_temp_accounts:WordPress Temporary Accounts
#ACLS:all

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Whostmgr::ACLS();
use Cpanel::JSON();
use CGI();

Whostmgr::ACLS::init_acls();

run() unless caller();

sub run {
    my $cgi = CGI->new();
    my $request_method = $ENV{REQUEST_METHOD} || 'GET';

    # Check permissions
    if (!Whostmgr::ACLS::hasroot()) {
        if ($request_method eq 'POST') {
            print_json_error('access_denied', 'Root access required');
        } else {
            print_html_error('Access Denied', 'You do not have access to this plugin.');
        }
        exit;
    }

    # Handle POST requests (API calls)
    if ($request_method eq 'POST') {
        handle_api_request($cgi);
    } else {
        # Handle GET requests (UI rendering)
        render_ui();
    }

    exit;
}

###############################################################################
# Logging and Audit Trail
###############################################################################

sub write_audit_log {
    my ($action, $details, $result) = @_;

    my $log_dir = '/var/log/wp_temp_accounts';
    my $log_file = "$log_dir/whm.log";

    # Ensure log directory exists
    unless (-d $log_dir) {
        mkdir($log_dir, 0750) or return;
        chown 0, 0, $log_dir;
    }

    # Sanitize inputs for logging
    $action = sanitize_log_input($action);
    $details = sanitize_log_input($details);
    $result = sanitize_log_input($result);

    # Format: timestamp | action | details | result | remote_ip
    my $timestamp = scalar localtime(time());
    my $remote_ip = $ENV{REMOTE_ADDR} || 'unknown';
    my $log_entry = sprintf("[%s] %s | %s | %s | %s\n",
        $timestamp, $action, $details, $result, $remote_ip);

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
    return 0 unless defined $days && $days =~ /^\d+$/;
    return $days >= 1 && $days <= 365;  # 1 day to 1 year max
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
    my ($cgi) = @_;

    # Read request body with size limit
    my $body = '';
    while (read STDIN, my $chunk, 8192) {
        $body .= $chunk;
        last if length($body) >= 65536;  # 64KB limit for DoS protection
    }

    my $request = eval { Cpanel::JSON::Load($body) };
    if ($@) {
        print_json_error('invalid_json', 'Invalid JSON request');
        return;
    }

    my $action = $request->{action} || '';
    my $payload = $request->{payload} || {};

    # Route to appropriate handler
    if ($action eq 'health') {
        print_json_success({ status => 'ok', uptime_sec => time() - $^T });
    }
    elsif ($action eq 'list_cpanel_accounts') {
        my $accounts = list_cpanel_accounts();
        print_json_success($accounts);
    }
    elsif ($action eq 'scan_wordpress') {
        my $account = $payload->{account} || '';
        my $sites = scan_wordpress($account);
        print_json_success($sites);
    }
    elsif ($action eq 'create_temp_user') {
        create_temp_user($payload);
    }
    elsif ($action eq 'list_temp_users') {
        my $users = list_temp_users($payload->{site_path});
        print_json_success($users);
    }
    elsif ($action eq 'delete_temp_user') {
        delete_temp_user($payload);
    }
    else {
        print_json_error('unknown_action', "Unknown action: $action");
    }
}

###############################################################################
# UI Rendering
###############################################################################

sub render_ui {
    print "Content-type: text/html; charset=utf-8\n\n";

    print <<'HTML';
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Temporary Accounts</title>
    <style>
        /* cPanel Jupiter Theme Compatible Styling */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f7f9fc;
            padding: 20px;
            font-size: 13px;
            color: #3c4858;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: linear-gradient(135deg, #1d8cf8 0%, #3358f4 100%);
            padding: 25px 30px;
            border-radius: 6px;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px 0px rgba(0, 0, 0, 0.14), 0 7px 10px -5px rgba(29, 140, 248, 0.4);
        }
        h1 {
            color: white;
            font-size: 22px;
            margin-bottom: 5px;
            font-weight: 400;
            letter-spacing: 0.3px;
        }
        .status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status.ok { background: rgba(255,255,255,0.2); color: white; }
        .status.error { background: rgba(255, 61, 61, 0.9); color: white; }
        .card {
            background: white;
            padding: 25px;
            border-radius: 6px;
            margin-bottom: 25px;
            box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.14);
            border: 1px solid #e3e3e3;
        }
        h2 {
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 20px;
            font-weight: 600;
            padding-bottom: 10px;
            border-bottom: 2px solid #1d8cf8;
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #525f7f;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        select, input {
            width: 100%;
            padding: 11px 16px;
            border: 1px solid #cad1d7;
            border-radius: 4px;
            font-size: 13px;
            color: #3c4858;
            transition: all 0.15s ease;
            background: white;
        }
        select:focus, input:focus {
            outline: none;
            border-color: #1d8cf8;
            box-shadow: 0 0 0 3px rgba(29, 140, 248, 0.1);
        }
        button {
            background: linear-gradient(60deg, #1d8cf8, #3358f4);
            color: white;
            border: none;
            padding: 11px 24px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
            transition: all 0.15s ease;
        }
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
        }
        button:disabled {
            background: #95a5a6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-danger {
            background: linear-gradient(60deg, #f5365c, #f56036);
            box-shadow: 0 4px 6px rgba(245, 54, 92, 0.3), 0 1px 3px rgba(0, 0, 0, 0.08);
        }
        .btn-danger:hover {
            box-shadow: 0 7px 14px rgba(245, 54, 92, 0.25), 0 3px 6px rgba(0, 0, 0, 0.08);
        }
        #loading {
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 15px 35px rgba(50, 50, 93, 0.2), 0 5px 15px rgba(0, 0, 0, 0.17);
            z-index: 1000;
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
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        th, td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #e3e3e3;
        }
        th {
            background: #f7f9fc;
            font-weight: 600;
            color: #525f7f;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }
        tr:hover { background: #f8f9fb; }
        tr:last-child td { border-bottom: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WordPress Temporary Accounts</h1>
            <div id="health-status" class="status ok">System: OK</div>
        </header>

        <div id="error-message"></div>
        <div id="loading">Loading...</div>

        <main>
            <!-- Step 1: Select cPanel Account -->
            <section class="card">
                <h2>1. Select cPanel Account</h2>
                <div class="form-group">
                    <label for="cpanel-account">cPanel Account:</label>
                    <select id="cpanel-account">
                        <option value="">Loading accounts...</option>
                    </select>
                </div>
                <button id="scan-btn" disabled>Scan for WordPress</button>
            </section>

            <!-- Step 2: Select WordPress Installation -->
            <section class="card" id="wp-installs-section" style="display:none;">
                <h2>2. Select WordPress Installation</h2>
                <div class="form-group">
                    <label for="wp-site">WordPress Site:</label>
                    <select id="wp-site">
                        <option value="">-- Select a WordPress site --</option>
                    </select>
                </div>
                <button id="load-users-btn" disabled>Load Users</button>
            </section>

            <!-- Step 3: Create Temporary User -->
            <section class="card" id="create-user-section" style="display:none;">
                <h2>3. Create Temporary User</h2>
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
                    <input type="number" id="days" value="7" min="1" max="365">
                </div>
                <button id="create-btn">Create Temporary User</button>
            </section>

            <!-- Step 4: Manage Users -->
            <section class="card" id="users-section" style="display:none;">
                <h2>4. Temporary Users</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Expires</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="users-table">
                        <tr><td colspan="4">No temporary users found</td></tr>
                    </tbody>
                </table>
            </section>
        </main>
    </div>

    <script>
        // State
        let state = { selectedAccount: null, selectedSite: null };

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

        // Load cPanel Accounts
        async function loadAccounts() {
            try {
                const accounts = await callAPI('list_cpanel_accounts');
                const select = document.getElementById('cpanel-account');
                select.innerHTML = '<option value="">-- Select an account --</option>';
                accounts.forEach(acc => {
                    const opt = document.createElement('option');
                    opt.value = acc.user;
                    opt.textContent = `${acc.user} (${acc.domain})`;
                    select.appendChild(opt);
                });
                select.disabled = false;
            } catch (error) {
                console.error('Failed to load accounts:', error);
            }
        }

        // Scan for WordPress
        async function scanWordPress() {
            const account = document.getElementById('cpanel-account').value;
            if (!account) return;

            state.selectedAccount = account;
            const sites = await callAPI('scan_wordpress', { account });

            const select = document.getElementById('wp-site');
            select.innerHTML = '<option value="">-- Select a site --</option>';
            sites.forEach(site => {
                const opt = document.createElement('option');
                opt.value = site.path;
                opt.textContent = `${site.domain} (${site.path})`;
                select.appendChild(opt);
            });
            select.disabled = false;
            document.getElementById('wp-installs-section').style.display = 'block';
        }

        // Load Users
        async function loadUsers() {
            const sitePath = document.getElementById('wp-site').value;
            if (!sitePath) return;

            state.selectedSite = sitePath;
            document.getElementById('create-user-section').style.display = 'block';
            document.getElementById('users-section').style.display = 'block';

            const users = await callAPI('list_temp_users', { site_path: sitePath });
            const tbody = document.getElementById('users-table');

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No temporary users found</td></tr>';
            } else {
                tbody.innerHTML = users.map(u => `
                    <tr>
                        <td>${u.username}</td>
                        <td>${u.email}</td>
                        <td>${u.expires}</td>
                        <td><button class="btn-danger" onclick="deleteUser('${u.username}')">Delete</button></td>
                    </tr>
                `).join('');
            }
        }

        // Create User
        async function createUser() {
            const username = document.getElementById('username').value;
            const email = document.getElementById('email').value;
            const days = document.getElementById('days').value;

            if (!username || !email) {
                showError('Username and email are required');
                return;
            }

            await callAPI('create_temp_user', {
                cpanel_user: state.selectedAccount,
                site_path: state.selectedSite,
                username,
                email,
                days: parseInt(days)
            });

            document.getElementById('username').value = '';
            document.getElementById('email').value = '';
            loadUsers();
        }

        // Delete User
        async function deleteUser(username) {
            if (!confirm(`Delete user ${username}?`)) return;
            await callAPI('delete_temp_user', {
                cpanel_user: state.selectedAccount,
                site_path: state.selectedSite,
                username
            });
            loadUsers();
        }

        // Event Listeners
        document.getElementById('cpanel-account').addEventListener('change', function() {
            document.getElementById('scan-btn').disabled = !this.value;
        });
        document.getElementById('scan-btn').addEventListener('click', scanWordPress);
        document.getElementById('wp-site').addEventListener('change', function() {
            document.getElementById('load-users-btn').disabled = !this.value;
        });
        document.getElementById('load-users-btn').addEventListener('click', loadUsers);
        document.getElementById('create-btn').addEventListener('click', createUser);

        // Initialize
        loadAccounts();
        callAPI('health').catch(() => {
            document.getElementById('health-status').textContent = 'System: Error';
            document.getElementById('health-status').className = 'status error';
        });
    </script>
</body>
</html>
HTML
}

###############################################################################
# Core Functions
###############################################################################

sub list_cpanel_accounts {
    my @accounts;

    # Read /etc/trueuserdomains
    if (open my $fh, '<', '/etc/trueuserdomains') {
        while (my $line = <$fh>) {
            chomp $line;
            next unless $line;
            my ($domain, $user) = split /:\s*/, $line, 2;
            next unless $user;

            # Get user info
            my $homedir = (getpwnam($user))[7] || "/home/$user";

            push @accounts, {
                user => $user,
                domain => $domain,
                homedir => $homedir
            };
        }
        close $fh;
    }

    return \@accounts;
}

sub scan_wordpress {
    my ($account) = @_;
    return [] unless $account;

    my $homedir = (getpwnam($account))[7];
    return [] unless $homedir && -d $homedir;

    my @sites;
    my @search_paths = (
        "$homedir/public_html",
        "$homedir/www",
        "$homedir/domains/*/public_html"
    );

    foreach my $search_path (@search_paths) {
        my @dirs = glob($search_path);
        foreach my $dir (@dirs) {
            next unless -d $dir;

            # Look for wp-config.php
            my $wp_config = "$dir/wp-config.php";
            if (-f $wp_config) {
                # Get domain from directory structure
                my $domain = $dir;
                $domain =~ s|.*/public_html||;
                $domain =~ s|.*/domains/([^/]+)/.*|$1|;
                $domain ||= 'public_html';

                push @sites, {
                    path => $dir,
                    domain => $domain,
                    wp_config => $wp_config
                };
            }
        }
    }

    return \@sites;
}

sub create_temp_user {
    my ($payload) = @_;

    my $cpanel_user = $payload->{cpanel_user} || '';
    my $site_path = $payload->{site_path} || '';
    my $username = $payload->{username} || '';
    my $email = $payload->{email} || '';
    my $days = $payload->{days} || 7;

    # Validate presence
    unless ($cpanel_user && $site_path && $username && $email) {
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

    # Validate site_path is under the account's homedir
    unless (validate_site_path($site_path, $cpanel_user)) {
        print_json_error('invalid_path', 'Invalid or unauthorized site path');
        return;
    }

    # Generate password
    my $password = generate_password();

    # Create user with WP-CLI
    my $expires = time() + ($days * 86400);
    my $cmd = qq{wp user create "$username" "$email" --role=administrator --user_pass="$password" --allow-root --path="$site_path" 2>&1};
    my $output = `$cmd`;

    if ($? != 0) {
        write_audit_log('CREATE_USER_FAILED', "user=$username site=$site_path", "error: $output");
        print_json_error('wp_cli_error', "Failed to create user: $output");
        return;
    }

    # Add expiration meta
    `wp user meta update "$username" wp_temp_user 1 --allow-root --path="$site_path"`;
    `wp user meta update "$username" wp_temp_expires $expires --allow-root --path="$site_path"`;

    # Log successful creation
    write_audit_log('CREATE_USER_SUCCESS', "user=$username site=$site_path days=$days", "success");

    print_json_success({
        username => $username,
        email => $email,
        password => $password,
        expires => scalar localtime($expires)
    });
}

sub list_temp_users {
    my ($site_path) = @_;
    return [] unless $site_path && -d $site_path;

    my @users;
    my $cmd = qq{wp user list --role=administrator --allow-root --path="$site_path" --format=json 2>&1};
    my $output = `$cmd`;

    if ($? == 0) {
        my $all_users = eval { Cpanel::JSON::Load($output) } || [];

        foreach my $user (@$all_users) {
            my $username = $user->{user_login};
            my $is_temp = `wp user meta get "$username" wp_temp_user --allow-root --path="$site_path" 2>&1`;
            chomp $is_temp;

            if ($is_temp eq '1') {
                my $expires = `wp user meta get "$username" wp_temp_expires --allow-root --path="$site_path" 2>&1`;
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
    my ($payload) = @_;

    my $site_path = $payload->{site_path} || '';
    my $username = $payload->{username} || '';

    unless ($site_path && $username) {
        print_json_error('missing_params', 'Missing required parameters');
        return;
    }

    my $cmd = qq{wp user delete "$username" --yes --allow-root --path="$site_path" 2>&1};
    my $output = `$cmd`;

    if ($? != 0) {
        write_audit_log('DELETE_USER_FAILED', "user=$username site=$site_path", "error: $output");
        print_json_error('wp_cli_error', "Failed to delete user: $output");
        return;
    }

    # Log successful deletion
    write_audit_log('DELETE_USER_SUCCESS', "user=$username site=$site_path", "success");

    print_json_success({ deleted => $username });
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
