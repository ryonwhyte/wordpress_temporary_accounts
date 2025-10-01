#!/bin/bash

###############################################################################
# WordPress Temporary Accounts - Uninstallation Script
# Clean removal from WHM and cPanel
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
echo " Uninstallation"
echo "======================================"
echo ""

# Ask about log preservation
read -p "Preserve logs in /var/log/wp-tempd? (y/n) " -n 1 -r
echo
PRESERVE_LOGS=$REPLY

# Stop and disable daemon
if systemctl is-active --quiet wp-tempd; then
    log_info "Stopping daemon..."
    systemctl stop wp-tempd
fi

if systemctl is-enabled --quiet wp-tempd 2>/dev/null; then
    log_info "Disabling daemon..."
    systemctl disable wp-tempd
fi

# Remove systemd service
if [ -f /etc/systemd/system/wp-tempd.service ]; then
    log_info "Removing systemd service..."
    rm -f /etc/systemd/system/wp-tempd.service
    systemctl daemon-reload
fi

# Unregister from WHM and cPanel
log_info "Unregistering from WHM..."
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts 2>/dev/null || true

log_info "Unregistering from cPanel..."
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true

# Remove WHM files
log_info "Removing WHM files..."
rm -rf /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
rm -f /var/cpanel/apps/wp_temp_accounts.conf

# Remove cPanel files
log_info "Removing cPanel files..."
rm -rf /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts
rm -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf

# Remove daemon files
log_info "Removing daemon files..."
rm -rf /usr/local/lib/wp-tempd

# Remove logs if requested
if [[ ! $PRESERVE_LOGS =~ ^[Yy]$ ]]; then
    log_info "Removing logs..."
    rm -rf /var/log/wp-tempd
else
    log_warn "Logs preserved in /var/log/wp-tempd"
fi

# Remove Unix socket if it exists
if [ -S /var/run/wp-tempd.sock ]; then
    log_info "Removing Unix socket..."
    rm -f /var/run/wp-tempd.sock
fi

# Restart WHM
log_info "Restarting cpsrvd..."
/scripts/restartsrv_cpsrvd --hard

echo ""
echo "======================================"
echo -e "${GREEN}Uninstallation Complete!${NC}"
echo "======================================"
echo ""

if [[ $PRESERVE_LOGS =~ ^[Yy]$ ]]; then
    echo "Logs are preserved in:"
    echo "  /var/log/wp-tempd/"
    echo ""
    echo "To remove logs manually:"
    echo "  rm -rf /var/log/wp-tempd"
    echo ""
fi
