#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';
use IPC::Open2;

# This wrapper executes the backend CGI with proper context
# It captures and forwards both the headers and body

# Set up environment for the backend
$ENV{'REQUEST_METHOD'} = 'POST';
$ENV{'CONTENT_TYPE'} = 'application/json';

# Read POST data
my $post_data = '';
my $buffer;
while (read(STDIN, $buffer, 4096)) {
    $post_data .= $buffer;
}

# Execute the backend CGI and capture its output
my ($chld_out, $chld_in);
my $pid = open2($chld_out, $chld_in, '/usr/local/cpanel/base/3rdparty/wp_temp_accounts/index.live.cgi');

# Send POST data to backend
print $chld_in $post_data;
close($chld_in);

# Read and forward the complete output from backend
while (<$chld_out>) {
    print $_;
}
close($chld_out);

waitpid($pid, 0);

1;