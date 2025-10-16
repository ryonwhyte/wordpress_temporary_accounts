# WordPress Temporary Accounts - Development Documentation

## Project Overview

A **dual-access WHM/cPanel plugin** for creating and managing temporary WordPress administrator accounts. Works in both **WHM** (system administrators managing all accounts) and **cPanel** (individual users managing their own sites).

## Current Architecture (v4.0)

**Pure Perl Implementation:**
- **Backend**: Perl CGI scripts with native cPanel modules
- **Frontend**: Template Toolkit templates (WHM master template integration)
- **WordPress Integration**: WP-CLI for user management
- **Security**: Root-level ACLs for WHM, user-scoped for cPanel
- **Cleanup**: Cron-based automatic expiration (hourly)

### Key Components:
1. **WHM Plugin** (`whm/wp_temp_accounts.cgi` + template)
2. **cPanel Plugin** (`cpanel/index.live.cgi` + template)
3. **Cleanup Script** (`cleanup_expired.pl`)
4. **Installation** (`install.sh` + `uninstall.sh`)

## Features (Latest)

### User Management
- ✅ **Create temporary admin users** with custom expiration (30 minutes to 365 days)
- ✅ **Password modal with copy-to-clipboard** (no more alert dialogs)
- ✅ **Tabbed interface** (Create User | Manage All Users)
- ✅ **Real-time filtering** by account/site/username/email
- ✅ **Persistent all-users view** across all WordPress sites

### WordPress Integration
- ✅ **Site discovery** via filesystem scanning (wp-config.php detection)
- ✅ **1-hour caching** of scan results for performance
- ✅ **WP-CLI integration** for safe user management
- ✅ **Metadata-based expiration** stored in WordPress usermeta

### Security & Access Control
- ✅ **WHM**: Full access to all cPanel accounts and WordPress sites
- ✅ **cPanel**: Scoped to logged-in user's sites only
- ✅ **Input validation** for usernames, emails, paths
- ✅ **Path traversal protection** (validates against homedirs)
- ✅ **Audit logging** with timestamps and IP addresses

### Automation
- ✅ **Hourly cron job** for automatic cleanup of expired accounts
- ✅ **Comprehensive logging** (`/var/log/wp_temp_accounts/`)

## User Interface

### WHM Interface
**Tab 1: Create User**
1. Select cPanel account
2. Scan for WordPress sites (with cache)
3. Select WordPress site
4. Create temporary user (username, email, expiration)
5. View password in modal with copy button

**Tab 2: Manage All Users**
- Table showing: cPanel Account | WordPress Site | Username | Email | Expires | Actions
- Filter by any field
- Delete users with confirmation

### cPanel Interface
**Tab 1: Create User**
1. Scan for WordPress sites (auto-scoped to logged-in user)
2. Select WordPress site
3. Create temporary user
4. View password in modal

**Tab 2: Manage All Users**
- Table showing: WordPress Site | Username | Email | Expires | Actions
- Filter by any field
- Delete users

## File Structure

```
wordpress_temporary_accounts/
├── whm/                          # WHM integration
│   ├── wp_temp_accounts.cgi      # Main CGI handler
│   └── wp_temp_accounts.tmpl     # Template Toolkit template
├── cpanel/                       # cPanel integration
│   ├── index.live.cgi            # cPanel CGI handler
│   ├── index.tmpl                # Template Toolkit template
│   ├── install.json              # DynamicUI registration
│   ├── group_wordpress.svg       # Group icon
│   └── wp_temp_accounts.svg      # Plugin icon
├── packaging/
│   ├── wp_temp_accounts.conf            # WHM AppConfig
│   ├── wp_temp_accounts_cpanel.conf     # cPanel AppConfig (legacy)
│   └── wp_temp_accounts_icon.png        # Plugin icon (48x48)
├── cleanup_expired.pl        # Cron cleanup script
├── install.sh                # Installation script
├── install_cron.sh           # Manual cron setup helper
├── uninstall.sh              # Uninstallation script
├── README.md                 # User documentation
├── LICENSE                   # MIT License
└── CLAUDE.md                 # This file (development docs)
```

## Installation

### Quick Install
```bash
cd wordpress_temporary_accounts
chmod +x install.sh
./install.sh
```

**What it does:**
1. Creates directories (`/var/log/wp_temp_accounts`, `/var/cache/wp_temp_accounts`)
2. Installs WHM plugin files
3. Installs cPanel plugin files (dynamicui method)
4. Registers WHM AppConfig
5. Sets up hourly cron job for cleanup
6. Restarts cpsrvd

### Manual Cron Setup
```bash
chmod +x install_cron.sh
./install_cron.sh
```

### Uninstall
```bash
./uninstall.sh
```

## API Actions

Both WHM and cPanel CGI scripts handle POST requests with JSON payloads:

### Common Actions
- **`health`** - System health check
- **`scan_wordpress`** - Scan for WordPress sites (with force_scan option)
- **`load_cached_wordpress`** - Load cached scan results
- **`create_temp_user`** - Create temporary admin user
- **`list_temp_users`** - List temp users for a specific site
- **`delete_temp_user`** - Delete a temporary user
- **`list_all_temp_users`** - Get all temp users (WHM: all accounts, cPanel: user's sites)

### WHM-Only Actions
- **`list_cpanel_accounts`** - Get all cPanel accounts on server

## Security

### Access Control
- **WHM**: Validates root access via `Whostmgr::ACLS::hasroot()`
- **cPanel**: Auto-scoped to `$ENV{REMOTE_USER}`
- **Path validation**: All site paths validated against user homedirs
- **Input sanitization**: Usernames, emails, paths validated before processing

### WordPress Operations
- **WP-CLI**: All operations run via WP-CLI (safe, WordPress-native)
- **User execution**: Commands run as cPanel user via `sudo -u`
- **Password generation**: 16-character random (alphanumeric + symbols)
- **Metadata storage**: Expiry stored in WordPress usermeta

### Audit Logging
- **Location**: `/var/log/wp_temp_accounts/`
- **Format**: Timestamp | User | Action | Details | Result | IP
- **Logs**: WHM actions, cPanel actions, cleanup operations

## WordPress User Management

### User Creation Strategy

1. **Username Generation**: `temp_admin_<timestamp>`
2. **Password**: 20-character random (uppercase, lowercase, numbers, symbols)
3. **Email**: `temp-<timestamp>@temporary.local`
4. **Role**: Administrator (configurable)
5. **Expiry Metadata**: Stored in `wp_usermeta` as `_temp_account_expires`

### Discovery Methods

**Primary: WP-CLI**
```bash
wp user list --path=/home/user/public_html
wp user create temp_user email@domain.com --role=administrator
```

**Fallback: Direct Database**
- Parse `wp-config.php` for credentials
- Connect to MySQL/MariaDB
- Insert into `wp_users` and `wp_usermeta` tables
- Use WordPress-compatible password hashing

## Cleanup Strategy

**Current**: Manual via daemon endpoint
**Future**: Cron job implementation

Cleanup process:
1. Query WordPress for users with `_temp_account_expires` metadata
2. Compare expiry timestamp to current time
3. Delete expired users via WP-CLI or direct database

## Development History & Key Fixes

### Major Challenges Overcome

**1. WHM Integration Issues**
- **Problem**: Plugin displayed as standalone page, not integrated with WHM
- **Solution**: Implemented Template Toolkit with `master_templates/master.tmpl` wrapper
- **Result**: Seamless integration like native WHM plugins

**2. JSON Request Handling**
- **Problem**: "Invalid JSON request" errors on all API calls
- **Solution**: Dual-mode POST body reading (CGI.pm POSTDATA + STDIN fallback)
- **Result**: Reliable API communication

**3. HTML Rendering Problems**
- **Problem**: Browser showing raw HTML source instead of rendered page
- **Solution**: Proper Template Toolkit usage (not heredoc strings)
- **Result**: Correct HTML rendering with WHM styling

**4. cPanel DynamicUI Integration**
- **Problem**: Plugin not appearing in cPanel interface
- **Solution**: Used `/scripts/install_plugin` with proper install.json
- **Result**: Native cPanel integration in Software section

### Architecture Evolution

**v1.0** - Initial Perl with WP Toolkit dependency
**v2.0** - Security hardening (input validation, CSRF protection)
**v3.0** - Universal compatibility (direct WordPress detection)
**v4.0** - Pure Perl with Template Toolkit (current)

### Latest Features (v4.0)
- ✅ Tabbed interface (Create | Manage All Users)
- ✅ Password modal with copy-to-clipboard
- ✅ Persistent all-users view with filtering
- ✅ Automatic cleanup via cron
- ✅ 1-hour caching for WordPress scans
- ✅ Comprehensive audit logging

## Troubleshooting

### Common Issues

**Plugin not appearing in WHM:**
```bash
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf
/scripts/restartsrv_cpsrvd --hard
```

**Plugin not appearing in cPanel:**
```bash
/usr/local/cpanel/scripts/install_plugin /path/to/wp_temp_accounts.tar.gz --theme jupiter
/scripts/restartsrv_cpsrvd --hard
```

**Cron not running:**
```bash
crontab -l | grep wp_temp_accounts_cleanup
./install_cron.sh  # If missing
```

**View logs:**
```bash
tail -f /var/log/wp_temp_accounts/whm.log
tail -f /var/log/wp_temp_accounts/cpanel.log
tail -f /var/log/wp_temp_accounts/cleanup.log
```

## Future Enhancements

### Possible Features
- Email notifications on user creation/expiration
- WordPress multisite support
- Custom capability management
- Bulk user operations
- Usage statistics/reporting

## License

MIT License - See LICENSE file for details

---

**Last Updated**: 2025-10-02
**Version**: 4.0 (Pure Perl with Template Toolkit)
**Author**: Ryon Whyte
