#!/bin/bash

###############################################################################
# WordPress Temporary Accounts - Pure Perl Uninstallation Script
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
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
echo "This will remove:"
echo "  • WHM plugin"
echo "  • cPanel plugin"
echo "  • All AppConfigs"
echo "  • All plugin files"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled"
    exit 0
fi

echo ""

# Unregister from WHM
log_info "Unregistering from WHM..."
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts 2>/dev/null || true

# Unregister from cPanel (both old AppConfig and new dynamicui methods)
log_info "Unregistering from cPanel..."
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts_cpanel 2>/dev/null || true

# Uninstall dynamicui plugin if installed
if [ -x /usr/local/cpanel/scripts/uninstall_plugin ]; then
    log_info "Removing dynamicui plugin registration..."
    /usr/local/cpanel/scripts/uninstall_plugin wp_temp_accounts --theme jupiter 2>/dev/null || true
fi

# Remove AppConfigs
log_info "Removing AppConfigs..."
rm -f /var/cpanel/apps/wp_temp_accounts.conf
rm -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf

# Remove WHM files
log_info "Removing WHM files..."
rm -rf /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
rm -rf /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
rm -f /usr/local/cpanel/whostmgr/docroot/addon_plugins/wp_temp_accounts_icon.png

# Remove cPanel files
log_info "Removing cPanel files..."
rm -rf /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts
rm -rf /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts

# Remove log directory
log_info "Removing log directory..."
rm -rf /var/log/wp_temp_accounts

# Remove cache directory
log_info "Removing cache directory..."
rm -rf /var/cache/wp_temp_accounts

# Verify removal
echo ""
log_info "Verifying removal..."

ERRORS=0

if [ -f /var/cpanel/apps/wp_temp_accounts.conf ]; then
    log_error "WHM AppConfig still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -f /var/cpanel/apps/wp_temp_accounts_cpanel.conf ]; then
    log_error "cPanel AppConfig still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -d /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts ]; then
    log_error "WHM directory still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -d /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts ]; then
    log_error "cPanel Jupiter directory still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -d /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts ]; then
    log_error "cPanel Paper Lantern directory still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -d /var/log/wp_temp_accounts ]; then
    log_error "Log directory still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ -d /var/cache/wp_temp_accounts ]; then
    log_error "Cache directory still exists"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    log_info "All files removed successfully"
else
    log_error "$ERRORS file(s) could not be removed"
    echo ""
    echo "You may need to manually remove remaining files"
    exit 1
fi

# Restart services
echo ""
log_info "Restarting cpsrvd..."
/scripts/restartsrv_cpsrvd --hard

echo ""
echo "======================================"
echo -e "${GREEN}Uninstallation Complete!${NC}"
echo "======================================"
echo ""
echo "All WordPress Temporary Accounts plugin"
echo "files have been removed from the system."
echo ""
