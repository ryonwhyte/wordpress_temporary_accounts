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
        '/usr/local/cpanel/3rdparty/bin/wp',
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

sub cleanup_expired_users {
    my $current_time = time();
    my $registry = load_registry();
    my @users = @{$registry->{users} || []};

    # Get WP-CLI path
    my $wp = get_wp_cli_path();

    my @remaining_users;
    my $deleted_count = 0;

    foreach my $user (@users) {
        my $cpanel_user = $user->{cpanel_account};
        my $site_path = $user->{site_path};
        my $username = $user->{username};
        my $expires = $user->{expires};

        # Check if expired
        if ($expires && $expires =~ /^\d+$/ && $expires < $current_time) {
            # Expired - attempt deletion from WordPress
            # Running as root via cron, so use sudo to run as cPanel user
            # Use sprintf with quotemeta for username only, not paths
            my $cmd = sprintf('%s user delete %s --yes --path="%s" 2>&1',
                $wp, quotemeta($username), $site_path);
            my ($output, $exit_code) = run_wp_cli($cmd, $cpanel_user);

            if ($exit_code == 0) {
                log_message("Deleted expired user: $username from $site_path (account: $cpanel_user)");
                $deleted_count++;
                # Do NOT add to remaining_users - it's deleted
            } else {
                log_message("Failed to delete user: $username from $site_path - $output");
                # Keep in registry even if delete failed (will retry next time)
                push @remaining_users, $user;
            }
        } else {
            # Not expired yet - keep in registry
            push @remaining_users, $user;
        }
    }

    # Update registry with remaining users
    $registry->{users} = \@remaining_users;
    save_registry($registry);

    return ($deleted_count, scalar(@users), scalar(@remaining_users));
}

# Main execution
log_message("Starting cleanup of expired temporary users (registry-based)");

my ($deleted, $total_before, $total_after) = cleanup_expired_users();

log_message("Cleanup complete. Before: $total_before users, Deleted: $deleted users, After: $total_after users");

exit 0;
