#!/usr/bin/perl

###############################################################################
# WordPress Temporary Accounts - Cleanup Script
# This script should be run via cron to remove expired temporary accounts
###############################################################################

use strict;
use warnings;
use Cpanel::JSON();

# Log file
my $log_file = '/var/log/wp_temp_accounts/cleanup.log';

sub log_message {
    my ($message) = @_;
    my $timestamp = scalar localtime(time());
    if (open my $fh, '>>', $log_file) {
        print $fh "[$timestamp] $message\n";
        close $fh;
    }
}

sub get_cpanel_accounts {
    my @accounts;

    # Get list of cPanel accounts from /etc/trueuserdomains
    if (open my $fh, '<', '/etc/trueuserdomains') {
        while (my $line = <$fh>) {
            chomp $line;
            if ($line =~ /^[^:]+:\s*(\S+)/) {
                push @accounts, $1;
            }
        }
        close $fh;
    }

    return @accounts;
}

sub find_wordpress_sites {
    my ($cpanel_user) = @_;
    my @sites;

    # Get user's home directory
    my $homedir = (getpwnam($cpanel_user))[7];
    return @sites unless $homedir;

    # Common WordPress locations
    my @search_paths = (
        "$homedir/public_html",
        "$homedir/www",
    );

    # Look for wp-config.php files
    foreach my $base_path (@search_paths) {
        next unless -d $base_path;

        my $cmd = qq{find "$base_path" -maxdepth 3 -name "wp-config.php" -type f 2>/dev/null};
        my @wp_configs = `$cmd`;

        foreach my $config_file (@wp_configs) {
            chomp $config_file;
            if ($config_file =~ m{^(.+)/wp-config\.php$}) {
                my $wp_path = $1;
                push @sites, $wp_path if -f "$wp_path/wp-login.php";
            }
        }
    }

    return @sites;
}

sub cleanup_expired_users {
    my ($cpanel_user, $site_path) = @_;
    my $current_time = time();
    my $deleted_count = 0;

    # Get list of administrator users
    my $cmd = qq{sudo -u $cpanel_user wp user list --role=administrator --path="$site_path" --format=json 2>&1};
    my $output = `$cmd`;

    return 0 unless $? == 0;

    my $all_users = eval { Cpanel::JSON::decode_json($output) } || [];

    foreach my $user (@$all_users) {
        my $username = $user->{user_login};

        # Check if this is a temporary user
        my $is_temp = `sudo -u $cpanel_user wp user meta get "$username" wp_temp_user --path="$site_path" 2>&1`;
        chomp $is_temp;

        next unless $is_temp eq '1';

        # Check expiration
        my $expires = `sudo -u $cpanel_user wp user meta get "$username" wp_temp_expires --path="$site_path" 2>&1`;
        chomp $expires;

        if ($expires && $expires =~ /^\d+$/ && $expires < $current_time) {
            # User is expired, delete it
            my $delete_cmd = qq{sudo -u $cpanel_user wp user delete "$username" --yes --path="$site_path" 2>&1};
            my $delete_output = `$delete_cmd`;

            if ($? == 0) {
                log_message("Deleted expired user: $username from $site_path (user: $cpanel_user)");
                $deleted_count++;
            } else {
                log_message("Failed to delete user: $username from $site_path - $delete_output");
            }
        }
    }

    return $deleted_count;
}

# Main execution
log_message("Starting cleanup of expired temporary users");

my @cpanel_accounts = get_cpanel_accounts();
my $total_deleted = 0;
my $total_sites = 0;

foreach my $cpanel_user (@cpanel_accounts) {
    my @sites = find_wordpress_sites($cpanel_user);

    foreach my $site_path (@sites) {
        $total_sites++;
        my $deleted = cleanup_expired_users($cpanel_user, $site_path);
        $total_deleted += $deleted;
    }
}

log_message("Cleanup complete. Checked $total_sites sites, deleted $total_deleted expired users");

exit 0;
