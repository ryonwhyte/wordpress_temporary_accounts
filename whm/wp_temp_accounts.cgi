#!/usr/local/cpanel/3rdparty/bin/perl
use strict;
use warnings;
use IO::Socket::UNIX;
use JSON ();

$|=1;
binmode STDIN;
binmode STDOUT;

sub out {
    print "Content-Type: application/json\r\n\r\n", JSON::encode_json($_[0]);
    exit 0;
}

# Security: Validate WHM context
(($ENV{REMOTE_USER}//'') eq 'root') or out({
    ok => JSON::false,
    error => { code => 'not_whm_root', message => 'This endpoint must be called from WHM' }
});

(($ENV{SERVER_PORT}//'') =~ /^(2086|2087)$/) or out({
    ok => JSON::false,
    error => { code => 'bad_port', message => 'Invalid server port' }
});

# Read request body
my $body = '';
while (read STDIN, my $b, 8192) {
    $body .= $b;
    length($body) < 65536 or out({
        ok => JSON::false,
        error => { code => 'payload_too_large', message => 'Request payload too large' }
    });
}

# Connect to Unix socket
my $sock = IO::Socket::UNIX->new(
    Type => SOCK_STREAM,
    Peer => "/var/run/wp-tempd.sock"
) or out({
    ok => JSON::false,
    error => { code => 'daemon_unavailable', message => 'Cannot connect to daemon' }
});

# Send request
print $sock ($body || '{}');
shutdown($sock, 1);

# Read response
my $resp = do { local $/; <$sock> } // '';
$resp or out({
    ok => JSON::false,
    error => { code => 'empty_response', message => 'No response from daemon' }
});

# Return response
print "Content-Type: application/json\r\n\r\n$resp";
