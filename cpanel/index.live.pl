#!/usr/local/cpanel/3rdparty/bin/perl

# WordPress Temporary Accounts - cPanel Plugin Entry Point
# This script redirects to the Template Toolkit file for proper rendering

use strict;
use warnings;

# Get the security token from environment
my $token = $ENV{'cp_security_token'} // '';

# Redirect to the Template Toolkit file
print "Status: 302 Found\r\n";
print "Location: ${token}/frontend/jupiter/wp_temp_accounts/index.html.tt\r\n\r\n";

1;