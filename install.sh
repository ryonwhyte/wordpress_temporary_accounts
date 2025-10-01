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
install -m 644 packaging/wp_temp_accounts.conf /var/cpanel/apps/
/usr/local/cpanel/bin/unregister_appconfig wordpress_temporary_accounts 2>/dev/null || true
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf

# Register with cPanel
log_info "Registering with cPanel..."
install -m 644 packaging/wp_temp_accounts_cpanel.conf /var/cpanel/apps/
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts_cpanel.conf

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
