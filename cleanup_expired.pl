#!/usr/bin/perl

###############################################################################
# WordPress Temporary Accounts - Cleanup Script
# This script should be run via cron to remove expired temporary accounts
# Now uses registry for instant lookups!
###############################################################################

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Cpanel::JSON();

# Registry file
my $registry_file = '/var/cache/wp_temp_accounts/registry.json';
my $log_file = '/var/log/wp_temp_accounts/cleanup.log';

# WP-CLI path detection
my $wp_cli_path_cache;

sub get_wp_cli_path {
    # Return cached path if already detected
    return $wp_cli_path_cache if $wp_cli_path_cache;

    # Try to find wp-cli in common locations
    my @possible_paths = (
        '/usr/local/bin/wp',
        '/usr/bin/wp',
        '/opt/cpanel/composer/bin/wp',
        '/usr/local/cpanel/3rdparty/bin/wp/',
    );

    # First try using 'which' command
    my $which_result = `which wp 2>/dev/null`;
    chomp $which_result;
    if ($which_result && -x $which_result) {
        $wp_cli_path_cache = $which_result;
        return $wp_cli_path_cache;
    }

    # Fall back to checking common paths
    foreach my $path (@possible_paths) {
        if (-x $path) {
            $wp_cli_path_cache = $path;
            return $wp_cli_path_cache;
        }
    }

    # Default to 'wp' and hope it's in PATH
    $wp_cli_path_cache = 'wp';
    return $wp_cli_path_cache;
}

sub run_wp_cli {
    my ($cmd, $cpanel_user) = @_;

    # WP-CLI detects CGI/web environment and refuses to run properly
    # Use env -i for clean environment

    # Cleanup script runs via cron as root
    # Run commands as the cPanel user who owns the WordPress installation
    if ($cpanel_user) {
        my $homedir = (getpwnam($cpanel_user))[7] || "/home/$cpanel_user";
        $cmd = sprintf('sudo -u %s env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=%s USER=%s %s',
            quotemeta($cpanel_user),
            quotemeta($homedir),
            quotemeta($cpanel_user),
            $cmd);
    } else {
        # Fallback if no user provided (shouldn't happen in cleanup context)
        $cmd = "env -i PATH=/usr/local/bin:/usr/bin:/bin $cmd";
    }

    # Execute the WP-CLI command
    my $output = `$cmd`;
    my $exit_code = $?;

    # Return output and exit code
    wantarray ? ($output, $exit_code) : $output;
}

sub log_message {
    my ($message) = @_;
    my $timestamp = scalar localtime(time());

    # Ensure log directory exists
    my $log_dir = '/var/log/wp_temp_accounts';
    unless (-d $log_dir) {
        mkdir($log_dir, 0750);
        chown 0, 0, $log_dir;
    }

    if (open my $fh, '>>', $log_file) {
        print $fh "[$timestamp] $message\n";
        close $fh;
    }
}

sub load_registry {
    return { users => [] } unless -f $registry_file;

    if (open my $fh, '<', $registry_file) {
        local $/;
        my $json = <$fh>;
        close $fh;

        my $data = eval { Cpanel::JSON::Load($json) };
        return $data if $data;
    }

    return { users => [] };
}

sub save_registry {
    my ($data) = @_;

    if (open my $fh, '>', $registry_file) {
        flock($fh, 2);  # LOCK_EX
        print $fh Cpanel::JSON::Dump($data);
        flock($fh, 8);  # LOCK_UN
        close $fh;

        chmod 0600, $registry_file;
        chown 0, 0, $registry_file;
        return 1;
    }

    return 0;
}

sub list_cpanel_accounts {
    my @accounts;

    # Read /etc/trueuserdomains
    if (open my $fh, '<', '/etc/trueuserdomains') {
        while (my $line = <$fh>) {
            chomp $line;
            next unless $line;
            my ($domain, $user) = split /:\s*/, $line, 2;
            next unless $user;

            push @accounts, {
                user => $user,
                domain => $domain
            };
        }
        close $fh;
    }

    return \@accounts;
}

sub scan_wordpress_sites {
    my ($cpanel_user) = @_;

    my $homedir = (getpwnam($cpanel_user))[7];
    return [] unless $homedir && -d $homedir;

    my @sites;
    my @search_roots = (
        "$homedir/public_html",
        "$homedir/www",
        glob("$homedir/domains/*/public_html")
    );

    foreach my $root (@search_roots) {
        next unless -d $root;
        find_wordpress_in_dir($root, \@sites);
    }

    return \@sites;
}

sub find_wordpress_in_dir {
    my ($dir, $sites_ref) = @_;

    # Check if wp-config.php exists
    if (-f "$dir/wp-config.php") {
        push @$sites_ref, { path => $dir };
        return;
    }

    # Scan subdirectories (max depth 3)
    opendir(my $dh, $dir) or return;
    my @subdirs = grep {
        $_ ne '.' && $_ ne '..' &&
        -d "$dir/$_" &&
        $_ !~ /^\./ &&
        $_ ne 'wp-admin' &&
        $_ ne 'wp-content' &&
        $_ ne 'wp-includes'
    } readdir($dh);
    closedir($dh);

    foreach my $subdir (@subdirs) {
        find_wordpress_in_dir("$dir/$subdir", $sites_ref);
    }
}

sub cleanup_expired_users {
    my $current_time = time();
    my $wp = get_wp_cli_path();

    my $deleted_count = 0;
    my $total_temp_users = 0;
    my @all_temp_users;

    # Get all cPanel accounts
    my $accounts = list_cpanel_accounts();
    log_message("Scanning " . scalar(@$accounts) . " cPanel accounts for temporary users");

    foreach my $account (@$accounts) {
        my $cpanel_user = $account->{user};

        # Get all WordPress sites for this account
        my $sites = scan_wordpress_sites($cpanel_user);

        foreach my $site (@$sites) {
            my $site_path = $site->{path};

            # Query WordPress for admin users
            my $cmd = sprintf('%s user list --role=administrator --path="%s" --format=json 2>&1',
                $wp, $site_path);
            my ($output, $exit_code) = run_wp_cli($cmd, $cpanel_user);

            if ($exit_code == 0) {
                my $all_users = eval { Cpanel::JSON::Load($output) };
                next unless $all_users && ref($all_users) eq 'ARRAY';

                foreach my $user (@$all_users) {
                    my $username = $user->{user_login};

                    # Check if this is a temp user
                    my $is_temp_cmd = sprintf('%s user meta get %s wp_temp_user --path="%s" 2>&1',
                        $wp, quotemeta($username), $site_path);
                    my $is_temp = run_wp_cli($is_temp_cmd, $cpanel_user);
                    chomp $is_temp;

                    if ($is_temp eq '1') {
                        $total_temp_users++;

                        # Get expiration time
                        my $expires_cmd = sprintf('%s user meta get %s wp_temp_expires --path="%s" 2>&1',
                            $wp, quotemeta($username), $site_path);
                        my $expires = run_wp_cli($expires_cmd, $cpanel_user);
                        chomp $expires;

                        # Check if expired
                        if ($expires && $expires =~ /^\d+$/ && $expires < $current_time) {
                            # Expired - get user ID for fallback
                            my $id_cmd = qq{$wp user get "$username" --field=ID --path="$site_path" 2>&1};
                            my ($id_output, $id_exit) = run_wp_cli($id_cmd, $cpanel_user);
                            chomp $id_output if $id_output;
                            my $user_id = ($id_exit == 0 && $id_output =~ /^(\d+)$/) ? $1 : undef;

                            # Delete by username
                            my $delete_cmd = qq{$wp user delete "$username" --yes --path="$site_path" 2>&1};
                            my ($delete_output, $delete_exit) = run_wp_cli($delete_cmd, $cpanel_user);

                            # Verify deletion
                            my $verify_cmd = qq{$wp user get "$username" --field=ID --path="$site_path" 2>&1};
                            my ($verify_out, $verify_exit) = run_wp_cli($verify_cmd, $cpanel_user);

                            if ($verify_exit != 0) {
                                # Confirmed deleted
                                log_message("Deleted expired user: $username from $site_path (account: $cpanel_user)");
                                $deleted_count++;
                            } elsif ($user_id) {
                                # Still exists - try by ID
                                log_message("User $username still exists after delete, trying by ID $user_id");
                                my $id_del_cmd = qq{$wp user delete $user_id --yes --path="$site_path" 2>&1};
                                my ($id_del_out, $id_del_exit) = run_wp_cli($id_del_cmd, $cpanel_user);

                                my ($final_out, $final_exit) = run_wp_cli($verify_cmd, $cpanel_user);
                                if ($final_exit != 0) {
                                    log_message("Deleted expired user by ID: $username (ID $user_id) from $site_path");
                                    $deleted_count++;
                                } else {
                                    log_message("Failed to delete user: $username from $site_path - persists after both attempts");
                                }
                            } else {
                                log_message("Failed to delete user: $username from $site_path - $delete_output");
                            }
                        } else {
                            # Not expired yet - keep for registry
                            push @all_temp_users, {
                                cpanel_account => $cpanel_user,
                                site_path => $site_path,
                                username => $username,
                                email => $user->{user_email},
                                expires => $expires
                            };
                        }
                    }
                }
            }
        }
    }

    # Update registry with current temp users (for record keeping)
    my $registry = { users => \@all_temp_users };
    save_registry($registry);

    my $remaining = scalar(@all_temp_users);
    return ($deleted_count, $total_temp_users, $remaining);
}

# Main execution
log_message("Starting cleanup of expired temporary users (WordPress scan)");

my ($deleted, $total_temp_users, $remaining) = cleanup_expired_users();

log_message("Cleanup complete. Found: $total_temp_users temp users, Deleted: $deleted expired users, Remaining: $remaining users");

exit 0;
