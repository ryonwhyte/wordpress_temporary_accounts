# WordPress Temporary Accounts - Pure Perl WHM Plugin

## Architecture

**FINAL IMPLEMENTATION:**
- ✅ Single self-contained Perl CGI script
- ✅ No Node.js, no daemon, no external dependencies
- ✅ All functionality in one file
- ✅ WP-CLI integration for WordPress operations
- ✅ Embedded HTML/CSS/JavaScript UI
- ✅ Follows cPanel/WHM official plugin standards

## File Structure

```
wordpress_temporary_accounts/
├── whm/
│   └── wp_temp_accounts.cgi          # Single unified CGI (570 lines)
├── packaging/
│   ├── wp_temp_accounts.conf         # AppConfig (TESTED - no uid/gid error)
│   └── wp_temp_accounts_icon.png     # Plugin icon
├── install.sh                        # Simplified installer (no Node.js)
├── uninstall.sh                      # Simplified uninstaller
├── DEPLOYMENT.md                     # This file
└── README.md                         # User documentation
```

## Installation

```bash
# Transfer to server
scp -r wordpress_temporary_accounts/ root@your-server:/root/

# SSH into server
ssh root@your-server

# Install
cd /root/wordpress_temporary_accounts
chmod +x install.sh
./install.sh
```

**Installation does:**
1. Creates directory: `/usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/`
2. Copies CGI script (755 permissions)
3. Copies icon (644 permissions)
4. Creates AppConfig with correct field order
5. Registers with WHM
6. Restarts cpsrvd

## AppConfig Details

**CRITICAL CONFIGURATION** (prevents uid/gid error):
```
name=wp_temp_accounts
service=whostmgr
url=/cgi/wp_temp_accounts/wp_temp_accounts.cgi
user=root                    # REQUIRED: Must be right after url
acls=all                     # REQUIRED: Must be after user=root
displayname=WordPress Temporary Accounts
entryurl=wp_temp_accounts/wp_temp_accounts.cgi
target=_self
icon=wp_temp_accounts_icon.png
```

**Field Order Matters:** Matches LiteSpeed plugin pattern exactly.

## Features

### Core Functionality
- List all cPanel accounts
- Scan for WordPress installations
- Create temporary administrator accounts
- Set expiration dates (1-365 days)
- List all temporary users
- Delete temporary users
- Automatic password generation

### Security
- Root-only access via `Whostmgr::ACLS::hasroot()`
- Path validation (prevents directory traversal)
- WP-CLI `--allow-root` flag for proper permissions
- Input sanitization
- Secure password generation

### WordPress Operations
Uses WP-CLI for all WordPress operations:
```bash
wp user create "$username" "$email" --role=administrator --allow-root --path="$site_path"
wp user meta update "$username" wp_temp_user 1 --allow-root --path="$site_path"
wp user meta update "$username" wp_temp_expires $timestamp --allow-root --path="$site_path"
wp user list --role=administrator --allow-root --path="$site_path" --format=json
wp user delete "$username" --yes --allow-root --path="$site_path"
```

## Usage

1. Access: **WHM → Plugins → WordPress Temporary Accounts**
2. Select cPanel account from dropdown
3. Click "Scan for WordPress" to find installations
4. Select WordPress site
5. Click "Load Users" to see existing temporary users
6. Create new temporary user:
   - Enter username
   - Enter email
   - Set expiration days
   - Click "Create Temporary User"
7. Password is auto-generated and displayed
8. Delete users via "Delete" button in table

## Technical Details

### Request Handling
```
GET  request → render_ui()        → HTML page with embedded JS
POST request → handle_api_request() → JSON response
```

### API Endpoints (via POST)
- `health` - System health check
- `list_cpanel_accounts` - Get all cPanel accounts
- `scan_wordpress` - Find WordPress installations
- `create_temp_user` - Create temporary WordPress user
- `list_temp_users` - List all temporary users
- `delete_temp_user` - Delete temporary user

### WordPress Detection
Scans these paths for `wp-config.php`:
- `/home/*/public_html`
- `/home/*/www`
- `/home/*/domains/*/public_html`

### Perl Modules Used
All standard cPanel modules:
- `Whostmgr::ACLS` - Permission checking
- `Cpanel::AcctUtils::DomainOwner::Tiny` - Account utilities
- `Cpanel::Config::LoadCpUserFile` - User config loading
- `Cpanel::JSON` - JSON encoding/decoding
- `CGI` - CGI request handling

## Troubleshooting

### Check Installation
```bash
ls -la /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
cat /var/cpanel/apps/wp_temp_accounts.conf
```

### Test CGI Directly
```bash
echo '{"action":"health"}' | REQUEST_METHOD=POST REMOTE_USER=root \
  /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi
```

### Check Perl Syntax
```bash
perl -c /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi
```

### View WHM Logs
```bash
tail -f /usr/local/cpanel/logs/error_log
```

### Verify WP-CLI
```bash
wp --info
```

## Uninstallation

```bash
cd /root/wordpress_temporary_accounts
./uninstall.sh
```

Removes:
- CGI script
- AppConfig
- WHM registration
- Restarts cpsrvd

## Why This Approach Works

### ✅ No "uid/gid for user: root" Error
- AppConfig has `user=root` in correct position
- Field order matches LiteSpeed plugin exactly
- Shell wrapper + `#ACLS:all` comment
- `Whostmgr::ACLS::init_acls()` + `hasroot()` check

### ✅ No External Dependencies
- Pure Perl (already in cPanel)
- No Node.js required
- No daemon to manage
- No systemd service
- No Unix sockets

### ✅ Simple Architecture
- One CGI file does everything
- GET → HTML, POST → JSON
- Direct WP-CLI execution
- Immediate response (no async)

### ✅ Reliable
- No daemon to crash
- No network dependencies
- Direct filesystem access
- Standard cPanel patterns

## Comparison: Old vs New

### Old (Node.js + Daemon)
```
Browser → WHM → wp_temp_accounts.cgi → api.cgi → Unix Socket → Node.js daemon → WP-CLI
```
**Issues:**
- Node.js dependency
- Daemon management
- Socket communication
- Complex debugging
- systemd service

### New (Pure Perl)
```
Browser → WHM → wp_temp_accounts.cgi → WP-CLI
```
**Benefits:**
- No dependencies
- Simple debugging
- Direct execution
- Standard cPanel pattern
- Reliable operation

## Success Criteria

✅ Plugin appears in WHM → Plugins menu
✅ No "Could not fetch uid or gid for user: root" error
✅ Interface loads with clean UI
✅ Can list cPanel accounts
✅ Can scan for WordPress sites
✅ Can create temporary users
✅ Can delete temporary users
✅ No external dependencies required

---

**Status:** Production-ready pure Perl WHM plugin
**Last Updated:** October 1, 2025
**Version:** 5.0 (Pure Perl)
