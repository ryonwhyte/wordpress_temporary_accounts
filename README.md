# WordPress Temporary Accounts WHM/cPanel Plugin

A simple, reliable plugin for creating temporary WordPress administrator accounts. Works in both **WHM** (for administrators) and **cPanel** (for individual users).

## Architecture

- **Backend**: Pure Perl (no Node.js dependency, native cPanel integration)
- **Frontend**: Template Toolkit templates with embedded JavaScript
- **WordPress Integration**: WP-CLI for all WordPress operations
- **Security**: Root-level access control for WHM, user-scoped for cPanel

## Features

- ✅ Create temporary WordPress admin accounts with custom expiration
- ✅ Automatic cleanup via hourly cron job
- ✅ Works with any WordPress installation
- ✅ **Dual access**: WHM (all accounts) and cPanel (per-user)
- ✅ Persistent view of all temporary users across all sites
- ✅ Copy-to-clipboard password display with modal
- ✅ WordPress site scanning with 1-hour cache
- ✅ No complex dependencies - uses existing cPanel infrastructure
- ✅ Comprehensive audit logging

## Access

- **WHM Users**: WHM → Plugins → WordPress Temporary Accounts (manage all sites)
- **cPanel Users**: cPanel → Software → WordPress Temporary Accounts (manage own sites)

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
│   ├── index.live.cgi             # cPanel CGI handler
│   ├── index.tmpl                 # cPanel Template Toolkit template
│   ├── install.json               # cPanel dynamicui registration
│   └── *.svg                      # Icons
├── packaging/              # Configuration files
│   ├── wp_temp_accounts.conf      # WHM AppConfig
│   ├── wp_temp_accounts_cpanel.conf  # cPanel AppConfig
│   └── wp_temp_accounts_icon.png  # Plugin icon
├── cleanup_expired.pl      # Cron script for expired account cleanup
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── README.md               # This file
└── CLAUDE.md               # Development documentation
```

## Automatic Cleanup

The plugin automatically removes expired temporary accounts via a cron job that runs every hour:

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

## Recent Fixes

### WP-CLI Path Detection and Command Execution Fix (2025-10-14)
Fixed critical issue where WP-CLI commands were returning garbage data instead of proper JSON:

**Problem**:
- When Perl executed WP-CLI commands via backticks, paths with `quotemeta()` were being escaped with backslashes
- Example: `/home/user/path` became `\/home\/user\/path`
- This caused WP-CLI to malfunction and return corrupted data instead of JSON
- Users appeared to be created successfully, but couldn't be listed because metadata queries returned garbage

**Root Cause**:
- `quotemeta()` escapes shell metacharacters INCLUDING forward slashes
- File paths should NOT be escaped with `quotemeta()` - only usernames need escaping
- The escaped paths confused WP-CLI internally

**Solution**:
1. Removed `quotemeta()` from all `--path=` arguments
2. Used double quotes around paths for proper handling of spaces: `--path="/home/user/path"`
3. Kept `quotemeta()` for usernames only (usernames can contain special chars like dots/hyphens)
4. Added dynamic WP-CLI path detection (`get_wp_cli_path()`) for portability across servers

**Files Modified**:
- `cpanel/index.cgi` - Fixed all WP-CLI command construction
- `whm/wp_temp_accounts.cgi` - Fixed all WP-CLI command construction
- `cleanup_expired.pl` - Fixed WP-CLI command construction
- All three files now properly detect WP-CLI location dynamically

**Result**: WP-CLI commands now return proper JSON, users are properly listed, and the plugin works correctly.

### cPanel Integration Issues Resolved (2025-10-11)
Fixed multiple issues preventing the cPanel plugin from appearing and functioning correctly:

1. **Menu Item Not Appearing**
   - Changed from non-existent "software" group to "domains" group
   - Fixed dynamicui config format (single-line, comma-separated)
   - Corrected `file=>` parameter to use base name only

2. **Icon Not Displaying**
   - Fixed icon reference in dynamicui config (`file=>wp_temp_accounts`)

3. **JSON Parsing Errors** ("Child failed to make LIVEAPI connection")
   - **Root cause**: Files with `.live.cgi` extension are automatically processed through cPanel's LiveAPI engine
   - **Solution**: Renamed backend from `index.live.cgi` to `index.cgi` to avoid LiveAPI processing
   - Added `X-No-SSI: 1` header to prevent SSI processing
   - Removed unused `Cpanel::LiveAPI` and `Cpanel::Template` modules from backend
   - Fixed POST data reading before CGI->new() consumes STDIN
   - Created `handle_api_request_direct()` for proper POST handling
   - **Key insight**: The `.live.cgi` extension triggers cPanel's LiveAPI parser, causing errors to be appended to output

4. **URL Redirect Issues**
   - Fixed `index.live.pl` to use simple relative path redirect
   - Prevents breaking cPanel URL structure

### Key Files Modified
- `cpanel/install.json` - Uses "domains" group
- `cpanel/index.live.pl` - Fixed redirect
- `cpanel/index.cgi` (renamed from index.live.cgi) - Removed unused modules, fixed POST handling, added X-No-SSI header
- `cpanel/index.html.tt` - Calls backend directly via `/3rdparty/` path
- `install.sh` - Updated dynamicui config format, uses index.cgi
- Removed `cpanel/api.live.pl` - No longer needed

## Troubleshooting

### Plugin not appearing in WHM
```bash
# Re-register the plugin
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf
/scripts/restartsrv_cpsrvd --hard
```

### Plugin not appearing in cPanel
```bash
# Clear caches and reinstall
rm -rf /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/*
rm -rf /home/*/.cpanel/caches/dynamicui/*
/usr/local/cpanel/bin/rebuild_sprites
/scripts/restartsrv_cpsrvd --hard

# Or do a fresh install
./uninstall.sh
./install.sh
```

### Cleanup not running
```bash
# Check cron job exists
crontab -l | grep wp_temp_accounts_cleanup

# Manually add cron job
echo "0 * * * * /usr/local/cpanel/scripts/wp_temp_accounts_cleanup >/dev/null 2>&1" | crontab -
```

### WP-CLI not working
```bash
# Verify WP-CLI is installed
wp --version

# Install WP-CLI if missing
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

## License

MIT License
