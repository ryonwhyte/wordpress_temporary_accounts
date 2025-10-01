#!/bin/bash

echo "=== Examining WHM Plugins on Server ==="
echo ""

echo "1. List all WHM CGI scripts:"
ls -lh /usr/local/cpanel/whostmgr/docroot/cgi/*.cgi 2>/dev/null | head -20

echo ""
echo "2. Check LiteSpeed plugin (lsws):"
if [ -f /usr/local/cpanel/whostmgr/docroot/cgi/lsws/lsws.cgi ]; then
    echo "Found: /usr/local/cpanel/whostmgr/docroot/cgi/lsws/lsws.cgi"
    head -50 /usr/local/cpanel/whostmgr/docroot/cgi/lsws/lsws.cgi
else
    echo "LiteSpeed CGI not found at expected location"
fi

echo ""
echo "3. Check Imunify360 plugin:"
if [ -d /usr/local/cpanel/whostmgr/docroot/cgi/imunify ]; then
    echo "Found Imunify360 directory"
    ls -lh /usr/local/cpanel/whostmgr/docroot/cgi/imunify/
    if [ -f /usr/local/cpanel/whostmgr/docroot/cgi/imunify/handlers/index.cgi ]; then
        echo ""
        echo "Imunify360 index.cgi (first 50 lines):"
        head -50 /usr/local/cpanel/whostmgr/docroot/cgi/imunify/handlers/index.cgi
    fi
fi

echo ""
echo "4. Check JetBackup5 plugin:"
if [ -d /usr/local/cpanel/whostmgr/docroot/cgi/addons/jetbackup5 ]; then
    echo "Found JetBackup5 directory"
    ls -lh /usr/local/cpanel/whostmgr/docroot/cgi/addons/jetbackup5/
    if [ -f /usr/local/cpanel/whostmgr/docroot/cgi/addons/jetbackup5/index.cgi ]; then
        echo ""
        echo "JetBackup5 index.cgi (first 50 lines):"
        head -50 /usr/local/cpanel/whostmgr/docroot/cgi/addons/jetbackup5/index.cgi
    fi
fi

echo ""
echo "5. Check WP Toolkit plugin:"
if [ -f /usr/local/cpanel/whostmgr/docroot/cgi/wp-toolkit/index.cgi ]; then
    echo "Found: /usr/local/cpanel/whostmgr/docroot/cgi/wp-toolkit/index.cgi"
    head -50 /usr/local/cpanel/whostmgr/docroot/cgi/wp-toolkit/index.cgi
fi

echo ""
echo "6. Check our plugin:"
if [ -f /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi ]; then
    echo "Found our plugin"
    ls -lh /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
fi
