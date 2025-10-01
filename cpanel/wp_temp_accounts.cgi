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
# API Request Handler
###############################################################################

sub handle_api_request {
    my ($cgi, $cpanel_user) = @_;

    # Read request body
    my $body = '';
    while (read STDIN, my $chunk, 8192) {
        $body .= $chunk;
        last if length($body) >= 65536;
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
        print_json_success({ status => 'ok', user => $cpanel_user });
    }
    elsif ($action eq 'scan_wordpress') {
        my $sites = scan_wordpress($cpanel_user);
        print_json_success($sites);
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
    else {
        print_json_error('unknown_action', "Unknown action: $action");
    }
}

###############################################################################
# UI Rendering
###############################################################################

sub render_ui {
    my ($cpanel_user) = @_;
    print "Content-type: text/html; charset=utf-8\n\n";

    print <<"HTML";
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Temporary Accounts</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; font-size: 24px; margin-bottom: 10px; }
        .user-info { color: #666; font-size: 14px; }
        .status { display: inline-block; padding: 5px 10px; border-radius: 4px; font-size: 14px; margin-top: 5px; }
        .status.ok { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { color: #333; font-size: 18px; margin-bottom: 15px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #555; font-weight: 500; }
        select, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        #loading { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 1000; }
        #error-message { display: none; background: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #f5c6cb; }
        #success-message { display: none; background: #d4edda; color: #155724; padding: 15px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #c3e6cb; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; color: #333; }
        tr:hover { background: #f8f9fa; }
        .password-display { background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WordPress Temporary Accounts</h1>
            <div class="user-info">Logged in as: <strong>$cpanel_user</strong></div>
            <div id="health-status" class="status ok">System: OK</div>
        </header>

        <div id="error-message"></div>
        <div id="success-message"></div>
        <div id="loading">Loading...</div>

        <main>
            <!-- Step 1: Select WordPress Installation -->
            <section class="card">
                <h2>1. Select WordPress Installation</h2>
                <p style="color: #666; margin-bottom: 15px;">Your WordPress sites will be listed below.</p>
                <div class="form-group">
                    <label for="wp-site">WordPress Site:</label>
                    <select id="wp-site">
                        <option value="">Loading sites...</option>
                    </select>
                </div>
                <button id="load-users-btn" disabled>Load Users</button>
            </section>

            <!-- Step 2: Create Temporary User -->
            <section class="card" id="create-user-section" style="display:none;">
                <h2>2. Create Temporary User</h2>
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" placeholder="temp_admin_123">
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" placeholder="temp\@example.com">
                </div>
                <div class="form-group">
                    <label for="days">Expiration (days):</label>
                    <input type="number" id="days" value="7" min="1" max="365">
                </div>
                <button id="create-btn">Create Temporary User</button>
                <div id="password-result" style="display:none; margin-top: 15px;">
                    <strong>User created successfully!</strong>
                    <div class="password-display">
                        <strong>Password:</strong> <span id="generated-password"></span>
                    </div>
                    <p style="color: #856404; margin-top: 10px;">⚠️ Save this password - it won't be shown again!</p>
                </div>
            </section>

            <!-- Step 3: Manage Users -->
            <section class="card" id="users-section" style="display:none;">
                <h2>3. Temporary Users</h2>
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
        function showSuccess(msg) {
            const el = document.getElementById('success-message');
            el.textContent = msg;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 5000);
        }

        // Load WordPress sites
        async function loadSites() {
            try {
                const sites = await callAPI('scan_wordpress');
                const select = document.getElementById('wp-site');

                if (sites.length === 0) {
                    select.innerHTML = '<option value="">No WordPress sites found</option>';
                } else {
                    select.innerHTML = '<option value="">-- Select a site --</option>';
                    sites.forEach(site => {
                        const opt = document.createElement('option');
                        opt.value = site.path;
                        opt.textContent = `\${site.domain} (\${site.path})`;
                        select.appendChild(opt);
                    });
                    select.disabled = false;
                }
            } catch (error) {
                console.error('Failed to load sites:', error);
            }
        }

        // Load Users
        async function loadUsers() {
            const sitePath = document.getElementById('wp-site').value;
            if (!sitePath) return;

            state.selectedSite = sitePath;
            document.getElementById('create-user-section').style.display = 'block';
            document.getElementById('users-section').style.display = 'block';
            document.getElementById('password-result').style.display = 'none';

            const users = await callAPI('list_temp_users', { site_path: sitePath });
            const tbody = document.getElementById('users-table');

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No temporary users found</td></tr>';
            } else {
                tbody.innerHTML = users.map(u => `
                    <tr>
                        <td>\${u.username}</td>
                        <td>\${u.email}</td>
                        <td>\${u.expires}</td>
                        <td><button class="btn-danger" onclick="deleteUser('\${u.username}')">Delete</button></td>
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

            const result = await callAPI('create_temp_user', {
                site_path: state.selectedSite,
                username,
                email,
                days: parseInt(days)
            });

            // Show password
            document.getElementById('generated-password').textContent = result.password;
            document.getElementById('password-result').style.display = 'block';

            // Clear form
            document.getElementById('username').value = '';
            document.getElementById('email').value = '';

            // Reload users
            loadUsers();
        }

        // Delete User
        async function deleteUser(username) {
            if (!confirm(`Delete user \${username}?`)) return;
            await callAPI('delete_temp_user', {
                site_path: state.selectedSite,
                username
            });
            showSuccess(`User \${username} deleted successfully`);
            loadUsers();
        }

        // Event Listeners
        document.getElementById('wp-site').addEventListener('change', function() {
            document.getElementById('load-users-btn').disabled = !this.value;
        });
        document.getElementById('load-users-btn').addEventListener('click', loadUsers);
        document.getElementById('create-btn').addEventListener('click', createUser);

        // Initialize
        loadSites();
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

sub scan_wordpress {
    my ($cpanel_user) = @_;

    my $homedir = (getpwnam($cpanel_user))[7];
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
    my ($cpanel_user, $payload) = @_;

    my $site_path = $payload->{site_path} || '';
    my $username = $payload->{username} || '';
    my $email = $payload->{email} || '';
    my $days = $payload->{days} || 7;

    # Validate
    unless ($site_path && $username && $email) {
        print_json_error('missing_params', 'Missing required parameters');
        return;
    }

    # Validate site_path is under the user's homedir
    my $homedir = (getpwnam($cpanel_user))[7];
    unless ($site_path =~ /^\Q$homedir\E\//) {
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
        print_json_error('wp_cli_error', "Failed to create user: $output");
        return;
    }

    # Add expiration meta
    `sudo -u $cpanel_user wp user meta update "$username" wp_temp_user 1 --path="$site_path"`;
    `sudo -u $cpanel_user wp user meta update "$username" wp_temp_expires $expires --path="$site_path"`;

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
        print_json_error('wp_cli_error', "Failed to delete user: $output");
        return;
    }

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
