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

# Install WHM plugin
log_info "Installing WHM plugin..."
install -m 755 whm/wp_temp_accounts.cgi /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/

# Install WHM template
log_info "Installing WHM template..."
mkdir -p /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
install -m 644 whm/wp_temp_accounts.tmpl /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/

# Install cPanel plugin
log_info "Installing cPanel plugin..."

# Jupiter (primary theme)
install -m 755 cpanel/wp_temp_accounts.cgi /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.cgi
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/

# Paper Lantern (legacy fallback)
install -m 755 cpanel/wp_temp_accounts.cgi /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/index.cgi 2>/dev/null || true
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/ 2>/dev/null || true

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

# Register with cPanel
log_info "Registering with cPanel..."

# Clean up old cPanel registration FIRST
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true

# Write cPanel AppConfig to temp file
TEMP_CPANEL_CONF=$(mktemp) || {
    log_error "Failed to create temp file for cPanel"
    exit 1
}

cat > "$TEMP_CPANEL_CONF" <<'EOF'
name=wp_temp_accounts_cpanel
service=cpanel
url=/frontend/jupiter/wp_temp_accounts/index.cgi
displayname=WordPress Temporary Accounts
entryurl=wp_temp_accounts/index.cgi
target=_self
icon=wp_temp_accounts_icon.png
EOF

# Verify temp file
if [ ! -s "$TEMP_CPANEL_CONF" ]; then
    log_error "Failed to write cPanel AppConfig to temp file"
    rm -f "$TEMP_CPANEL_CONF"
    exit 1
fi

# Move to final location
if ! mv "$TEMP_CPANEL_CONF" /var/cpanel/apps/wp_temp_accounts_cpanel.conf; then
    log_error "Failed to move cPanel AppConfig"
    rm -f "$TEMP_CPANEL_CONF"
    exit 1
fi

# Set permissions
chmod 644 /var/cpanel/apps/wp_temp_accounts_cpanel.conf
chown root:root /var/cpanel/apps/wp_temp_accounts_cpanel.conf

# Verify file exists
if [ ! -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf ]; then
    log_error "cPanel AppConfig file not created"
    exit 1
fi

# Register cPanel config
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts_cpanel.conf || {
    log_error "Failed to register cPanel AppConfig"
    log_error "File contents:"
    cat /var/cpanel/apps/wp_temp_accounts_cpanel.conf
    exit 1
}

log_info "cPanel plugin registered successfully"

# Set proper ownership and permissions
log_info "Setting file permissions..."
chown -R root:root /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
chown -R root:root /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
chown -R root:root /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts 2>/dev/null || true
chown root:root /var/log/wp_temp_accounts
chmod 0750 /var/log/wp_temp_accounts

# Restart services
log_info "Restarting cpsrvd..."
/scripts/restartsrv_cpsrvd --hard

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
echo ""
