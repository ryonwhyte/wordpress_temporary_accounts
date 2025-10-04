#!/usr/bin/sh
eval 'if [ -x /usr/local/cpanel/3rdparty/bin/perl ]; then exec /usr/local/cpanel/3rdparty/bin/perl -x -- $0 ${1+"$@"}; else exec /usr/bin/perl -x -- $0 ${1+"$@"};fi'
if 0;
#!/usr/bin/perl

use strict;
use warnings;
use lib '/usr/local/cpanel';

# This is a simple wrapper that executes the backend CGI with proper context
# It ensures the session and authentication are properly passed through

# Set up environment for the backend
$ENV{'REQUEST_METHOD'} = 'POST';
$ENV{'CONTENT_TYPE'} = 'application/json';

# Read POST data
my $post_data = '';
my $buffer;
while (read(STDIN, $buffer, 4096)) {
    $post_data .= $buffer;
}

# Execute the backend CGI
open(my $cgi, '|-', '/usr/local/cpanel/base/3rdparty/wp_temp_accounts/index.live.cgi') or die "Cannot execute backend: $!";
print $cgi $post_data;
close($cgi);

1;