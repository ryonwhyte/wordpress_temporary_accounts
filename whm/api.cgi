#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';
use Whostmgr::ACLS();
use IO::Socket::UNIX;
use JSON ();

Whostmgr::ACLS::init_acls();

run() unless caller();

sub run {
    # Check permissions
    if (!Whostmgr::ACLS::hasroot()) {
        print "Content-Type: application/json\r\n\r\n";
        print JSON::encode_json({
            ok => JSON::false,
            error => { code => 'access_denied', message => 'Root access required' }
        });
        exit;
    }

    # Read request body
    my $body = '';
    while (read STDIN, my $b, 8192) {
        $body .= $b;
        last if length($body) >= 65536;
    }

    # Connect to Unix socket
    my $sock = IO::Socket::UNIX->new(
        Type => SOCK_STREAM,
        Peer => "/var/run/wp-tempd.sock"
    );

    if (!$sock) {
        print "Content-Type: application/json\r\n\r\n";
        print JSON::encode_json({
            ok => JSON::false,
            error => { code => 'daemon_unavailable', message => 'Cannot connect to daemon' }
        });
        exit;
    }

    # Forward request
    print $sock ($body || '{}');
    shutdown($sock, 1);

    # Read response
    my $resp = do { local $/; <$sock> } // '';

    # Return response
    print "Content-Type: application/json\r\n\r\n";
    print $resp || JSON::encode_json({
        ok => JSON::false,
        error => { code => 'empty_response', message => 'No response from daemon' }
    });

    exit;
}
