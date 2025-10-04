#!/usr/local/cpanel/3rdparty/bin/perl

# WordPress Temporary Accounts - cPanel Plugin Wrapper
# This wrapper loads the template through cPanel's Template Toolkit system

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Cpanel::Template ();

# Load and process the template
my $template = Cpanel::Template->new();
$template->process(
    'wp_temp_accounts/index.html.tt',
    {
        'theme' => $ENV{'CPANEL_THEME'} || 'jupiter',
        'user'  => $ENV{'REMOTE_USER'} || 'unknown',
    }
);

1;