#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Cpanel::JSON();
use Cpanel::Template();
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

    # Use Cpanel::Template to process the template file
    print "Content-type: text/html\r\n\r\n";

    # Process template with cPanel's Template system
    my $result = Cpanel::Template::process_template(
        'cpanel',
        {
            'template_file' => 'wp_temp_accounts/index.tmpl',
            'print'         => 1,
            'cpanel_user'   => $cpanel_user,
        }
    );

    # If template processing fails, show a simple fallback interface
    unless ($result) {
        print_fallback_ui($cpanel_user);
    }

    return;
}

sub print_fallback_ui {
    my ($cpanel_user) = @_;

    # Fallback to a simple HTML interface if template fails
    print <<'HTML';
<!DOCTYPE html>
<html>
<head>
    <title>WordPress Temporary Accounts</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .error { background: #fee; padding: 10px; border: 1px solid #fcc; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>WordPress Temporary Accounts</h1>
        <div class="error">
            <p>The template rendering failed. Using fallback interface.</p>
            <p>Please check that the template file exists at:</p>
            <code>/usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.tmpl</code>
        </div>
        <p>User: <strong>
HTML
    print $cpanel_user;
    print <<'HTML';
        </strong></p>
        <p>Please contact your administrator if this issue persists.</p>
    </div>
</body>
</html>
HTML
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

