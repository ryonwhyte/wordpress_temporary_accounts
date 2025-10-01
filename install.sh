#!/bin/bash

###############################################################################
# WordPress Temporary Accounts - Installation Script
# Installs for both WHM (administrators) and cPanel (users)
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
echo " Installation"
echo "======================================"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed"
    log_info "Installing Node.js..."

    # Install Node.js from NodeSource
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs

    log_info "Node.js installed: $(node --version)"
else
    log_info "Node.js found: $(node --version)"
fi

# Check PHP
if ! command -v php &> /dev/null; then
    log_warn "PHP not found, installing..."
    yum install -y ea-php74
fi

# Create directories
log_info "Creating directories..."
mkdir -p /usr/local/lib/wp-tempd
mkdir -p /var/log/wp-tempd
mkdir -p /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
mkdir -p /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts

# Install daemon
log_info "Installing daemon..."
cp daemon/server.js /usr/local/lib/wp-tempd/
cp daemon/package.json /usr/local/lib/wp-tempd/

# Install Node modules
cd /usr/local/lib/wp-tempd
npm install --production --quiet
cd -

# Install systemd service
log_info "Installing systemd service..."
cp packaging/wp-tempd.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable wp-tempd
systemctl restart wp-tempd

# Check daemon status
if systemctl is-active --quiet wp-tempd; then
    log_info "Daemon started successfully"
else
    log_error "Daemon failed to start"
    systemctl status wp-tempd --no-pager
    exit 1
fi

# Install WHM files
log_info "Installing WHM integration..."
install -m 755 whm/wp_temp_accounts.cgi /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 755 whm/api.cgi /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 644 whm/frontend/index.html /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 644 whm/frontend/app.js /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 644 whm/frontend/style.css /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/

# Install cPanel files
log_info "Installing cPanel integration..."
install -m 755 cpanel/proxy.php /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/
install -m 644 cpanel/frontend/index.html /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/
install -m 644 cpanel/frontend/app.js /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/
install -m 644 cpanel/frontend/style.css /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/
install -m 644 packaging/wp_temp_accounts_icon.png /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/

# Register with WHM
log_info "Registering with WHM..."

# Clean up any old registrations FIRST (before creating new file)
/usr/local/cpanel/bin/unregister_appconfig wordpress_temporary_accounts 2>/dev/null || true
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts 2>/dev/null || true

# Ensure directory exists
if ! mkdir -p /var/cpanel/apps 2>&1; then
    log_error "Failed to create /var/cpanel/apps directory"
    exit 1
fi

log_info "Writing AppConfig to /var/cpanel/apps/wp_temp_accounts.conf"

# Check if /var/cpanel/apps is writable
if [ ! -w /var/cpanel/apps ]; then
    log_error "/var/cpanel/apps is not writable"
    ls -ld /var/cpanel/apps
    exit 1
fi

# Write AppConfig to temp file first, then move it
TEMP_CONF=$(mktemp) || {
    log_error "Failed to create temp file"
    exit 1
}

log_info "Created temp file: $TEMP_CONF"

cat > "$TEMP_CONF" <<'EOF'
name=wp_temp_accounts
service=whostmgr
user=root
group=plugins
itemorder=1
url=/cgi/wp_temp_accounts/wp_temp_accounts.cgi
entryurl=wp_temp_accounts/wp_temp_accounts.cgi
displayname=WordPress Temporary Accounts
icon=/cgi/wp_temp_accounts/wp_temp_accounts_icon.png
acls=all
EOF

# Verify temp file was created and has content
if [ ! -s "$TEMP_CONF" ]; then
    log_error "Failed to write AppConfig to temp file"
    rm -f "$TEMP_CONF"
    exit 1
fi

log_info "Temp file size: $(wc -c < "$TEMP_CONF") bytes"
log_info "Moving temp file to /var/cpanel/apps/wp_temp_accounts.conf"

# Move to final location
if ! mv "$TEMP_CONF" /var/cpanel/apps/wp_temp_accounts.conf; then
    log_error "Failed to move temp file to /var/cpanel/apps/"
    rm -f "$TEMP_CONF"
    exit 1
fi

log_info "File moved successfully"

# Verify file exists immediately after move
if [ ! -f /var/cpanel/apps/wp_temp_accounts.conf ]; then
    log_error "File disappeared immediately after move!"
    ls -la /var/cpanel/apps/ | grep wp
    exit 1
fi

log_info "File exists after move, setting permissions..."

# Set permissions
if ! chmod 644 /var/cpanel/apps/wp_temp_accounts.conf; then
    log_error "chmod failed"
    exit 1
fi

if ! chown root:root /var/cpanel/apps/wp_temp_accounts.conf; then
    log_error "chown failed"
    exit 1
fi

# Verify file still exists after permissions
if [ ! -f /var/cpanel/apps/wp_temp_accounts.conf ]; then
    log_error "File disappeared after setting permissions!"
    ls -la /var/cpanel/apps/ | grep wp
    exit 1
fi

log_info "Permissions set successfully"

# Register new config (old registrations already cleaned up above)
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf || {
    log_error "Failed to register WHM AppConfig"
    log_error "File contents:"
    cat /var/cpanel/apps/wp_temp_accounts.conf
    exit 1
}

# Register with cPanel
log_info "Registering with cPanel..."

# Unregister old cPanel app FIRST (before creating new file)
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true

# Write cPanel AppConfig to temp file first
TEMP_CPANEL_CONF=$(mktemp)
cat > "$TEMP_CPANEL_CONF" <<'EOF'
name=wp_temp_accounts_cpanel
service=cpanel
group=software
itemorder=1
url=/frontend/paper_lantern/wp_temp_accounts/index.html
entryurl=wp_temp_accounts/index.html
displayname=WordPress Temporary Accounts
icon=/frontend/paper_lantern/wp_temp_accounts/wp_temp_accounts_icon.png
acls=all
EOF

# Verify temp file was created and has content
if [ ! -s "$TEMP_CPANEL_CONF" ]; then
    log_error "Failed to write cPanel AppConfig to temp file"
    rm -f "$TEMP_CPANEL_CONF"
    exit 1
fi

# Move to final location
mv "$TEMP_CPANEL_CONF" /var/cpanel/apps/wp_temp_accounts_cpanel.conf

# Set permissions
chmod 644 /var/cpanel/apps/wp_temp_accounts_cpanel.conf
chown root:root /var/cpanel/apps/wp_temp_accounts_cpanel.conf

# Verify file was created
if [ ! -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf ]; then
    log_error "cPanel AppConfig file not created"
    exit 1
fi

# Register new config (old registration already cleaned up above)
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts_cpanel.conf || {
    log_error "Failed to register cPanel AppConfig"
    log_error "File contents:"
    cat /var/cpanel/apps/wp_temp_accounts_cpanel.conf
    exit 1
}

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
echo "Daemon status:"
echo "  systemctl status wp-tempd"
echo ""
echo "Logs:"
echo "  /var/log/wp-tempd/wp-tempd.log"
echo "  journalctl -u wp-tempd -f"
echo ""
