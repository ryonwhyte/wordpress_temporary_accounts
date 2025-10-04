#!/bin/bash

###############################################################################
# WordPress Temporary Accounts - Pure Perl Installation Script
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

echo "======================================"
echo " WordPress Temporary Accounts"
echo " Pure Perl Installation (WHM + cPanel)"
echo "======================================"
echo ""

# Create directories
log_info "Creating directories..."
mkdir -p /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts
mkdir -p /var/log/wp_temp_accounts
mkdir -p /var/cache/wp_temp_accounts

# Create empty registry file
log_info "Creating registry file..."
echo '{"users":[]}' > /var/cache/wp_temp_accounts/registry.json
chmod 0600 /var/cache/wp_temp_accounts/registry.json
chown root:root /var/cache/wp_temp_accounts/registry.json

# Install WHM plugin
log_info "Installing WHM plugin..."
install -m 755 whm/wp_temp_accounts.cgi /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/

# Install WHM icon to addon_plugins directory
log_info "Installing WHM icon..."
mkdir -p /usr/local/cpanel/whostmgr/docroot/addon_plugins
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/whostmgr/docroot/addon_plugins/

# Install WHM template
log_info "Installing WHM template..."
mkdir -p /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
install -m 644 whm/wp_temp_accounts.tmpl /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/

# Install cPanel plugin
log_info "Installing cPanel plugin files..."

# Create plugin directories for both themes
mkdir -p /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/3rdparty/wp_temp_accounts

# Install CGI backend to 3rdparty directory (for proper execution context)
install -m 755 cpanel/index.live.cgi /usr/local/cpanel/base/3rdparty/wp_temp_accounts/

# Install to both Jupiter and Paper Lantern themes
for theme in jupiter paper_lantern; do
    log_info "Installing for $theme theme..."

    # Install the live.pl wrapper script (entry point from dynamicui)
    install -m 755 cpanel/index.live.pl /usr/local/cpanel/base/frontend/$theme/wp_temp_accounts/

    # Install the HTML template
    install -m 644 cpanel/index.html.tt /usr/local/cpanel/base/frontend/$theme/wp_temp_accounts/

    # Install icons
    install -m 644 cpanel/group_wordpress.svg /usr/local/cpanel/base/frontend/$theme/wp_temp_accounts/
    install -m 644 cpanel/wp_temp_accounts.svg /usr/local/cpanel/base/frontend/$theme/wp_temp_accounts/
done

# Create plugin tarball for install_plugin script
log_info "Creating plugin package..."
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/wp_temp_accounts"

# Copy install.json to root (required by install_plugin)
cp cpanel/install.json "$TEMP_DIR/install.json"

# Copy all necessary files to plugin directory
cp cpanel/index.live.pl "$TEMP_DIR/wp_temp_accounts/"
cp cpanel/group_wordpress.svg "$TEMP_DIR/wp_temp_accounts/"
cp cpanel/wp_temp_accounts.svg "$TEMP_DIR/wp_temp_accounts/"

# Create the tar file with the correct structure
cd "$TEMP_DIR"
tar -czf wp_temp_accounts.tar.gz install.json wp_temp_accounts/
cd - >/dev/null

# Install plugin using official install_plugin script for both themes
log_info "Registering cPanel plugin with install_plugin..."
if /usr/local/cpanel/scripts/install_plugin "$TEMP_DIR/wp_temp_accounts.tar.gz" --theme jupiter; then
    log_info "Jupiter theme plugin installed successfully"
else
    log_warn "Jupiter theme plugin installation had issues"
fi

if /usr/local/cpanel/scripts/install_plugin "$TEMP_DIR/wp_temp_accounts.tar.gz" --theme paper_lantern; then
    log_info "Paper Lantern theme plugin installed successfully"
else
    log_warn "Paper Lantern theme plugin installation had issues"
fi

rm -rf "$TEMP_DIR"

# Clear cPanel UI caches
log_info "Clearing cPanel caches..."
rm -f /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/* 2>/dev/null || true
rm -f /usr/local/cpanel/base/frontend/paper_lantern/.cpanelcache/* 2>/dev/null || true

# Remove any old dynamicui configurations from previous attempts
log_info "Cleaning up old configurations..."
rm -f /usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wp_temp_accounts.conf 2>/dev/null || true
rm -f /usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wptemp*.conf 2>/dev/null || true
rm -f /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/install.json 2>/dev/null || true

log_info "cPanel plugin registered successfully"

# Register with WHM
log_info "Registering with WHM..."

# Clean up any old registrations FIRST
/usr/local/cpanel/bin/unregister_appconfig wordpress_temporary_accounts 2>/dev/null || true
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts 2>/dev/null || true

# Ensure directory exists
mkdir -p /var/cpanel/apps

# Write AppConfig to temp file
TEMP_CONF=$(mktemp) || {
    log_error "Failed to create temp file"
    exit 1
}

cat > "$TEMP_CONF" <<'EOF'
name=wp_temp_accounts
service=whostmgr
url=/cgi/wp_temp_accounts/wp_temp_accounts.cgi
user=root
acls=all
displayname=WordPress Temporary Accounts
entryurl=wp_temp_accounts/wp_temp_accounts.cgi
target=_self
icon=wp_temp_accounts_icon.png
EOF

# Verify temp file
if [ ! -s "$TEMP_CONF" ]; then
    log_error "Failed to write AppConfig to temp file"
    rm -f "$TEMP_CONF"
    exit 1
fi

# Move to final location
if ! mv "$TEMP_CONF" /var/cpanel/apps/wp_temp_accounts.conf; then
    log_error "Failed to move AppConfig"
    rm -f "$TEMP_CONF"
    exit 1
fi

# Set permissions
chmod 644 /var/cpanel/apps/wp_temp_accounts.conf
chown root:root /var/cpanel/apps/wp_temp_accounts.conf

# Verify file exists
if [ ! -f /var/cpanel/apps/wp_temp_accounts.conf ]; then
    log_error "AppConfig file not created"
    exit 1
fi

log_info "AppConfig created successfully"

# Register WHM config
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf || {
    log_error "Failed to register WHM AppConfig"
    log_error "File contents:"
    cat /var/cpanel/apps/wp_temp_accounts.conf
    exit 1
}

log_info "WHM plugin registered successfully"

# Note: cPanel plugin registration is handled by install_plugin script above (dynamicui method)
# Clean up old AppConfig registration if it exists
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true
rm -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf 2>/dev/null || true

log_info "cPanel plugin installation complete"

# Set proper ownership and permissions
log_info "Setting file permissions..."
chown -R root:root /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
chown -R root:root /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
chown root:root /usr/local/cpanel/whostmgr/docroot/addon_plugins/wp_temp_accounts_icon.png
chown -R root:root /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
chown -R root:root /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts
chown -R root:root /usr/local/cpanel/base/3rdparty/wp_temp_accounts
# Make scripts executable
chmod 755 /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.live.pl
chmod 755 /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/index.live.pl
chmod 755 /usr/local/cpanel/base/3rdparty/wp_temp_accounts/index.live.cgi
chown root:root /var/log/wp_temp_accounts
chmod 0750 /var/log/wp_temp_accounts
chown root:root /var/cache/wp_temp_accounts
chmod 0750 /var/cache/wp_temp_accounts

# Install cleanup script
log_info "Installing cleanup script..."
install -m 755 cleanup_expired.pl /usr/local/cpanel/scripts/wp_temp_accounts_cleanup

# Install log rotation configuration
log_info "Installing log rotation configuration..."
install -m 644 logrotate.conf /etc/logrotate.d/wp_temp_accounts

# Set up cron job for automatic cleanup (runs every hour)
log_info "Setting up cron job..."
CRON_JOB="0 * * * * /usr/local/cpanel/scripts/wp_temp_accounts_cleanup >/dev/null 2>&1"
(crontab -l 2>/dev/null | grep -v "wp_temp_accounts_cleanup"; echo "$CRON_JOB") | crontab -

# Clear caches and restart services
log_info "Clearing template cache..."
rm -f /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/* 2>/dev/null || true
rm -f /usr/local/cpanel/whostmgr/.cpanelcache/* 2>/dev/null || true

log_info "Restarting cpsrvd..."
/scripts/restartsrv_cpsrvd --hard

log_info "Rebuilding WHM session cache..."
/usr/local/cpanel/bin/rebuild_sprites 2>/dev/null || true

echo ""
echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "======================================"
echo ""
echo "Access the plugin:"
echo "  WHM: WHM → Plugins → WordPress Temporary Accounts"
echo "  cPanel: cPanel → Software → WordPress Temporary Accounts"
echo ""
echo "Features:"
echo "  • Pure Perl (no Node.js dependency)"
echo "  • WHM: Manage all sites (root access)"
echo "  • cPanel: Users manage their own sites"
echo "  • WP-CLI integration for WordPress operations"
echo "  • Automatic cleanup: Cron runs hourly to remove expired users"
echo ""
echo "Logs:"
echo "  • Cleanup log: /var/log/wp_temp_accounts/cleanup.log"
echo "  • cPanel log: /var/log/wp_temp_accounts/cpanel.log"
echo ""
echo "======================================"
echo "IMPORTANT - Verification Steps:"
echo "======================================"
echo ""
echo "The cPanel URL should be:"
echo "  ✓ https://yourserver:2083/frontend/jupiter/wp_temp_accounts/index.live.pl"
echo "  ✗ NOT: .../wp_temp_accounts/index.live.cgi (direct CGI access)"
echo "  ✗ NOT: .../wp_temp_accounts/index.html.tt (template file)"
echo ""
echo "To access the plugin:"
echo "  1. Log out of cPanel completely"
echo "  2. Clear browser cache (Ctrl+Shift+Del)"
echo "  3. Log back into cPanel"
echo "  4. Look for 'WordPress Tools' → 'WordPress Temporary Accounts'"
echo ""
echo "To verify installation:"
echo "  ls -la /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/"
echo ""
