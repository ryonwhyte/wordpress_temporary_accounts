#!/bin/bash

echo "=== Debug 500 Error ==="
echo ""

echo "1. Check cpsrvd error log (last 20 lines):"
tail -20 /usr/local/cpanel/logs/error_log 2>/dev/null || echo "Cannot read error_log"

echo ""
echo "2. Check if our CGI has syntax errors:"
perl -c /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi 2>&1

echo ""
echo "3. Check CGI permissions:"
ls -la /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/*.cgi

echo ""
echo "4. Test running the CGI directly:"
echo '{}' | REQUEST_METHOD=POST REMOTE_USER=root SERVER_PORT=2087 /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi 2>&1 | head -30

echo ""
echo "5. Check if required Perl modules are available:"
perl -e 'use lib "/usr/local/cpanel"; use Whostmgr::ACLS; print "Whostmgr::ACLS loaded OK\n";' 2>&1

echo ""
echo "6. Check cpsrvd access log for our requests:"
tail -5 /usr/local/cpanel/logs/access_log | grep wp_temp_accounts 2>/dev/null || echo "No recent requests found"
