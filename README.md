# WordPress Temporary Accounts WHM/cPanel Plugin

A simple, reliable plugin for creating temporary WordPress administrator accounts. Works in both **WHM** (for administrators) and **cPanel** (for individual users).

**Version**: 4.2.0

## Architecture

- **Backend**: Pure Perl (no Node.js dependency, native cPanel integration)
- **Frontend**: Template Toolkit templates with embedded JavaScript
- **WordPress Integration**: WP-CLI for all WordPress operations
- **Security**: Root-level access control for WHM, user-scoped for cPanel

## Features

- Create temporary WordPress admin accounts with custom expiration (5 minutes to 365 days)
- Automatic cleanup via hourly cron job
- Works with any WordPress installation
- **Dual access**: WHM (all accounts) and cPanel (per-user)
- **2FA plugin management**: Optionally disable 2FA plugins during temp user sessions, auto-re-enables on deletion/expiry
- Persistent view of all temporary users across all sites
- Copy-to-clipboard password display with modal
- WordPress site scanning with 1-hour cache
- Comprehensive audit logging
- **Self-update** from GitHub (WHM only)
- Post-delete verification with fallback deletion by user ID
- No complex dependencies - uses existing cPanel infrastructure

## Access

- **WHM Users**: WHM > Plugins > WordPress Temporary Accounts (manage all sites)
- **cPanel Users**: cPanel > Software > WordPress Temporary Accounts (manage own sites)

## Installation

```bash
cd wordpress_temporary_accounts
chmod +x install.sh
./install.sh
```

The installation script will:
1. Install WHM and cPanel plugins
2. Set up automatic cleanup cron job (runs hourly)
3. Create log directories
4. Register with WHM and cPanel interfaces
5. Restart cpsrvd service

## Usage

### Creating a Temporary User

1. Select a cPanel account (WHM only) and WordPress site
2. Set username, email, and expiration period
3. Optionally disable a detected 2FA plugin for the temp user's session
4. Click Create - password is displayed in a modal with copy button

### 2FA Plugin Management

When a WordPress site has an active 2FA plugin (e.g., Wordfence, WP 2FA, Google Authenticator), the plugin can be temporarily disabled so the temp user can log in without a 2FA prompt. The plugin is automatically re-activated when:
- The temp user is manually deleted
- The temp user expires and is cleaned up by cron

If multiple temp users have the same 2FA plugin disabled, it only re-activates when the **last** such user is removed.

**Supported 2FA plugins**: Wordfence, Wordfence Login Security, Two-Factor, Google Authenticator, WP 2FA, miniOrange 2FA, Duo, All In One WP Security, iThemes Security / Solid Security, Shield Security.

### Self-Update (WHM Only)

WHM includes a built-in update button that pulls the latest version from GitHub and re-runs the installer.

## Technology Stack

- **Perl** - Backend logic (uses native cPanel modules)
- **Template Toolkit** - UI rendering (WHM and cPanel native)
- **WP-CLI** - WordPress user management
- **cron** - Automatic cleanup of expired accounts

## Directory Structure

```
wordpress_temporary_accounts/
├── whm/                    # WHM integration (administrators)
│   ├── wp_temp_accounts.cgi       # WHM CGI handler
│   └── wp_temp_accounts.tmpl      # WHM Template Toolkit template
├── cpanel/                 # cPanel integration (users)
│   ├── index.cgi                  # cPanel CGI handler
│   ├── index.html.tt              # cPanel Template Toolkit template
│   ├── install.json               # cPanel dynamicui registration
│   └── *.svg                      # Icons
├── packaging/              # Configuration files
│   ├── wp_temp_accounts.conf      # WHM AppConfig
│   ├── wp_temp_accounts_cpanel.conf  # cPanel AppConfig
│   └── wp_temp_accounts_icon.png  # Plugin icon
├── cleanup_expired.pl      # Cron script for expired account cleanup
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
└── README.md               # This file
```

## Automatic Cleanup

The plugin automatically removes expired temporary accounts via a cron job that runs every hour. The cleanup script scans all cPanel accounts and WordPress installations directly (not dependent on registry accuracy).

```bash
# View cleanup logs
tail -f /var/log/wp_temp_accounts/cleanup.log

# Manually run cleanup
/usr/local/cpanel/scripts/wp_temp_accounts_cleanup
```

## Logs

- **Cleanup log**: `/var/log/wp_temp_accounts/cleanup.log`
- **WHM audit log**: `/var/log/wp_temp_accounts/whm.log`
- **cPanel log**: `/var/log/wp_temp_accounts/cpanel.log`

## Troubleshooting

### Plugin not appearing in WHM
```bash
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf
/scripts/restartsrv_cpsrvd --hard
```

### Plugin not appearing in cPanel
```bash
rm -rf /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/*
rm -rf /home/*/.cpanel/caches/dynamicui/*
/usr/local/cpanel/bin/rebuild_sprites
/scripts/restartsrv_cpsrvd --hard
```

### Cleanup not running
```bash
# Check cron job exists
crontab -l | grep wp_temp_accounts_cleanup

# Manually add if missing
echo "0 * * * * /usr/local/cpanel/scripts/wp_temp_accounts_cleanup >/dev/null 2>&1" | crontab -
```

### WP-CLI not working
```bash
wp --version

# Install if missing
curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
mv wp-cli.phar /usr/local/bin/wp
```

## Security

- **WHM access**: Requires root privileges (validated via `Whostmgr::ACLS::hasroot()`)
- **cPanel access**: Automatically scoped to logged-in user's sites only
- **Input validation**: All user inputs are validated before processing
- **Path traversal protection**: Site paths are validated against account homedirs
- **Audit logging**: All user creation/deletion actions are logged with timestamps and IP addresses
- **Post-delete verification**: Confirms user was actually removed from WordPress before updating registry

## License

MIT License
