#!/usr/local/cpanel/3rdparty/bin/perl

# WordPress Temporary Accounts - cPanel Plugin
# This script serves as the entry point for the cPanel plugin

use strict;
use warnings;

# Set proper content type
print "Content-type: text/html\r\n\r\n";

# Determine the theme
my $theme = $ENV{'CPANEL_THEME'} || 'jupiter';

# Read and output the HTML template directly
# The template contains JavaScript that will make AJAX calls to the backend CGI
my $template_file = "/usr/local/cpanel/base/frontend/$theme/wp_temp_accounts/index.html.tt";

if (-e $template_file) {
    open(my $fh, '<', $template_file) or die "Cannot open template: $!";
    while (my $line = <$fh>) {
        # Simple template variable replacement
        $line =~ s/\{\{CPANEL_USER\}\}/$ENV{'REMOTE_USER'} || 'unknown'/ge;
        $line =~ s/\{\{CPANEL_THEME\}\}/$theme/ge;
        $line =~ s/\{\{BACKEND_URL\}\}/\/3rdparty\/wp_temp_accounts\/index.live.cgi/ge;
        print $line;
    }
    close($fh);
} else {
    print <<HTML;
<!DOCTYPE html>
<html>
<head>
    <title>WordPress Temporary Accounts</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Configuration Error</h1>
    <p>The template file could not be found. Please ensure the plugin is properly installed.</p>
    <p>Expected location: $template_file</p>
    <p>Theme: $theme</p>
</body>
</html>
HTML
}

1;