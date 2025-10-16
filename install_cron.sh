#!/bin/bash

###############################################################################
# WordPress Temporary Accounts - Cron Job Installation Helper
# Use this script to manually install/verify the cleanup cron job
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
echo " Cron Job Installation"
echo "======================================"
echo ""

# Verify cleanup script exists
CLEANUP_SCRIPT="/usr/local/cpanel/scripts/wp_temp_accounts_cleanup"
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    log_error "Cleanup script not found at $CLEANUP_SCRIPT"
    log_error "Please run install.sh first"
    exit 1
fi

# Make sure it's executable
chmod 755 "$CLEANUP_SCRIPT"
log_info "Cleanup script verified and executable"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "wp_temp_accounts_cleanup"; then
    log_warn "Cron job already exists:"
    crontab -l 2>/dev/null | grep "wp_temp_accounts_cleanup"
    echo ""
    read -p "Do you want to reinstall it? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing cron job"
        exit 0
    fi

    # Remove existing cron job
    log_info "Removing existing cron job..."
    (crontab -l 2>/dev/null | grep -v "wp_temp_accounts_cleanup") | crontab -
fi

# Add cron job (runs every hour at minute 0)
log_info "Installing cron job..."
CRON_JOB="0 * * * * /usr/local/cpanel/scripts/wp_temp_accounts_cleanup >/dev/null 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

# Verify installation
if crontab -l 2>/dev/null | grep -q "wp_temp_accounts_cleanup"; then
    log_info "Cron job installed successfully!"
    echo ""
    echo "Current cron entry:"
    crontab -l 2>/dev/null | grep "wp_temp_accounts_cleanup"
    echo ""
    echo "The cleanup script will run every hour to remove expired temporary accounts."
    echo ""
    echo "To manually run cleanup:"
    echo "  $CLEANUP_SCRIPT"
    echo ""
    echo "To view cleanup logs:"
    echo "  tail -f /var/log/wp_temp_accounts/cleanup.log"
    echo ""
else
    log_error "Failed to install cron job"
    exit 1
fi

echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "======================================"
