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

# Install cPanel plugin (Template Toolkit method)
log_info "Installing cPanel plugin..."

# Create plugin directories
mkdir -p /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/3rdparty/wp_temp_accounts

# Install CGI script to 3rdparty directory (for execution)
install -m 755 cpanel/index.cgi /usr/local/cpanel/base/3rdparty/wp_temp_accounts/

# Install template and assets to frontend directory
install -m 644 cpanel/index.tmpl /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/

# Install icons
install -m 644 cpanel/group_wordpress.svg /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/
install -m 644 cpanel/wp_temp_accounts.svg /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/

# Install install.json for dynamicui
install -m 644 cpanel/install.json /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/

# Create plugin tarball for install_plugin script with correct structure
log_info "Creating plugin package..."
TEMP_DIR=$(mktemp -d)

# Create the plugin directory structure as required by install_plugin
mkdir -p "$TEMP_DIR/wp_temp_accounts"
cp cpanel/install.json "$TEMP_DIR/install.json"  # install.json must be at root of tar
cp cpanel/index.tmpl "$TEMP_DIR/wp_temp_accounts/"
cp cpanel/*.svg "$TEMP_DIR/wp_temp_accounts/"

# Create the tar file with the correct structure (use -C to change directory)
tar -czf "$TEMP_DIR/wp_temp_accounts.tar.gz" -C "$TEMP_DIR" install.json wp_temp_accounts

# Install plugin using official install_plugin script
if [ -x /usr/local/cpanel/scripts/install_plugin ]; then
    log_info "Registering cPanel plugin with dynamicui..."
    /usr/local/cpanel/scripts/install_plugin "$TEMP_DIR/wp_temp_accounts.tar.gz" --theme jupiter

    # If install_plugin succeeded, we don't need the manual configuration
    if [ $? -eq 0 ]; then
        log_info "Plugin registered successfully via install_plugin"
        rm -rf "$TEMP_DIR"
    else
        log_warn "install_plugin failed, using manual registration..."
        rm -rf "$TEMP_DIR"

        # Manual fallback will be handled below
    fi
else
    log_info "install_plugin script not found, using manual dynamicui registration..."
    rm -rf "$TEMP_DIR"
fi

# Clear cPanel UI caches
log_info "Clearing cPanel caches..."
rm -f /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/* 2>/dev/null || true

# Clean up any old cPanel AppConfig (from older versions)
log_info "Cleaning up old AppConfig entries..."
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true
rm -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf 2>/dev/null || true

# Remove any old manual dynamicui configurations
rm -f /usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wp_temp_accounts.conf 2>/dev/null || true
rm -f /usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wptemp*.conf 2>/dev/null || true

log_info "cPanel plugin files installed"

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
chown -R root:root /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts 2>/dev/null || true
chown root:root /var/log/wp_temp_accounts
chmod 0750 /var/log/wp_temp_accounts
chown root:root /var/cache/wp_temp_accounts
chmod 0750 /var/cache/wp_temp_accounts

# Install cleanup script
log_info "Installing cleanup script..."
install -m 755 cleanup_expired.pl /usr/local/cpanel/scripts/wp_temp_accounts_cleanup

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
echo "  ✓ https://yourserver:2083/frontend/jupiter/index.html?app=wp_temp_accounts"
echo "  ✗ NOT: .../wp_temp_accounts/index.tmpl (raw template = config error)"
echo ""
echo "To access the plugin:"
echo "  1. Log out of cPanel completely"
echo "  2. Clear browser cache (Ctrl+Shift+Del)"
echo "  3. Log back into cPanel"
echo "  4. Look for 'WordPress Tools' → 'WordPress Temporary Accounts'"
echo ""
echo "To verify installation:"
echo "  grep -R '\"id\": \"wp_temp_accounts\"' /usr/local/cpanel/base/frontend/jupiter -n"
echo ""
