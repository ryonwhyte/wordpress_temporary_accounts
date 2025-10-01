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

Whostmgr::ACLS::init_acls();

run() unless caller();

sub run {
    print "Content-type: text/html; charset=utf-8\n\n";

    # Check permissions
    if (!Whostmgr::ACLS::hasroot()) {
        print "<h1>Access Denied</h1>\n";
        print "<p>You do not have access to the WordPress Temporary Accounts plugin.</p>\n";
        exit;
    }

    # Serve the HTML file
    my $html_file = '/usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/index.html';
    if (open my $fh, '<', $html_file) {
        local $/;
        print <$fh>;
        close $fh;
    } else {
        print "<h1>Error</h1>\n";
        print "<p>Cannot load plugin interface.</p>\n";
    }

    exit;
}
