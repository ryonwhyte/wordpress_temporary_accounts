#!/usr/local/cpanel/3rdparty/bin/perl

# WordPress Temporary Accounts - API Wrapper for cPanel
# This wrapper ensures the backend CGI is called with proper cPanel context

use strict;
use warnings;

# Set up the environment for the actual CGI
$ENV{'REQUEST_METHOD'} = 'POST';
$ENV{'CONTENT_TYPE'} = 'application/json';

# Read the POST data
my $post_data = '';
while (<STDIN>) {
    $post_data .= $_;
}

# Execute the actual backend CGI with the POST data
open(my $cgi, '|-', '/usr/local/cpanel/base/3rdparty/wp_temp_accounts/index.live.cgi') or die "Cannot execute backend: $!";
print $cgi $post_data;
close($cgi);

1;