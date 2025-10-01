# WordPress Temporary Accounts - Development Documentation

## Project Overview

This is a **dual-access plugin** for creating and managing temporary WordPress administrator accounts. It works in both **WHM** (for system administrators managing all accounts) and **cPanel** (for individual users managing their own sites). This project represents a complete architectural rebuild from a complex Perl-based implementation to a simple, reliable Node.js/PHP stack.

## Architecture Decision

### Why the Rebuild?

After 2 days of troubleshooting Perl-based WHM plugin issues, the decision was made to completely rebuild using familiar, reliable technologies:

**Previous Architecture (Abandoned):**
- Perl CGI with complex cPanel modules
- Multiple dependency issues (Cpanel::PwCache, etc.)
- Complex variable scoping problems
- Hard to debug and maintain

**Current Architecture (Production):**
- **Node.js daemon** - Backend service handling all WordPress operations
- **PHP proxies** - Minimal integration layer for both WHM and cPanel
- **Static HTML/CSS/JS** - Clean, modern frontend (separate for WHM and cPanel)
- **Unix socket** - Secure IPC with no network exposure

## Technology Stack

### Backend: Node.js Daemon (`daemon/server.js`)
- **Runtime**: Node.js 18+
- **Communication**: Unix socket at `/var/run/wp-tempd.sock`
- **Protocol**: JSON-RPC for simple request/response
- **Service Management**: systemd (`wp-tempd.service`)
- **Logging**: File-based logging to `/var/log/wp-tempd/wp-tempd.log`

**Key Features:**
- WordPress site discovery (via WP-CLI and filesystem scanning)
- Temporary user creation with metadata-based expiration
- cPanel account enumeration
- Health check endpoint
- Automatic cleanup (future: cron integration)

### WHM Integration: PHP Proxy (`whm/proxy.php`)
- **Purpose**: Bridge between WHM and Node.js daemon
- **Security**: Validates WHM context (root user, ports 2086/2087)
- **Function**: Forwards JSON requests to Unix socket
- **Access**: All cPanel accounts, can manage any WordPress site

### cPanel Integration: PHP Proxy (`cpanel/proxy.php`)
- **Purpose**: Bridge between cPanel and Node.js daemon
- **Security**: Validates cPanel user context, auto-injects user into requests
- **Function**: Forwards JSON requests to Unix socket
- **Access**: Restricted to logged-in user's WordPress sites only
- **Allowed Actions**: `health`, `list_wp_installs`, `create_temp_user` (no `list_cpanel_accounts`)

### Frontend (WHM: `whm/frontend/`, cPanel: `cpanel/frontend/`)
- **index.html** - Clean wizard interface
- **app.js** - State management and API communication
- **style.css** - Modern, responsive styling

**WHM User Flow:**
1. Select cPanel account
2. Scan for WordPress installations
3. Choose WordPress site and configure user
4. Display credentials with expiry information

**cPanel User Flow:**
1. Scan for WordPress installations (auto-scoped to their account)
2. Choose WordPress site and configure user
3. Display credentials with expiry information

## File Structure

```
wordpress_temporary_accounts/
├── daemon/
│   ├── server.js           # Node.js backend (195 lines)
│   └── package.json        # Dependencies (express, winston)
├── whm/                    # WHM integration (administrators)
│   ├── proxy.php           # WHM proxy (validates root user)
│   └── frontend/
│       ├── index.html      # WHM UI (with account selector)
│       ├── app.js          # WHM frontend logic
│       └── style.css       # Styling
├── cpanel/                 # cPanel integration (users)
│   ├── proxy.php           # cPanel proxy (auto-injects user)
│   └── frontend/
│       ├── index.html      # cPanel UI (no account selector)
│       ├── app.js          # cPanel frontend logic
│       └── style.css       # Styling
├── packaging/
│   ├── wp-tempd.service           # systemd service definition
│   ├── wp_temp_accounts.conf      # WHM AppConfig
│   ├── wp_temp_accounts_cpanel.conf  # cPanel AppConfig
│   └── wp_temp_accounts_icon.png  # 48x48 PNG icon
├── install.sh              # Installation script (both WHM + cPanel)
├── uninstall.sh            # Uninstallation script (both WHM + cPanel)
├── README.md               # User documentation
├── LICENSE                 # MIT License
└── CLAUDE.md               # This file
```

## Installation Details

### Installation Script (`install.sh`)

**What it does:**
1. Checks root privileges
2. Installs Node.js 18+ (via NodeSource if missing)
3. Verifies PHP is available
4. Creates required directories:
   - `/usr/local/lib/wp-tempd` - Daemon installation
   - `/var/log/wp-tempd` - Log directory
   - `/usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts` - WHM files
   - `/usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts` - cPanel files
5. Installs and starts daemon as systemd service
6. Installs WHM files (proxy, frontend, icon)
7. Installs cPanel files (proxy, frontend, icon)
8. Registers plugin with WHM via AppConfig
9. Registers plugin with cPanel via AppConfig
10. Restarts cpsrvd

**Usage:**
```bash
cd wordpress_temporary_accounts
chmod +x install.sh
./install.sh
```

### Uninstallation Script (`uninstall.sh`)

**What it does:**
1. Stops and disables wp-tempd service
2. Removes systemd service file
3. Unregisters from WHM
4. Removes all installed files
5. Optionally preserves logs

**Usage:**
```bash
./uninstall.sh
```

## API Endpoints (Daemon)

The Node.js daemon exposes these actions via JSON-RPC:

### `health`
- **Purpose**: Check daemon status
- **Payload**: None
- **Response**: `{ status: "ok", uptime_sec: 1234 }`

### `list_cpanel_accounts`
- **Purpose**: Get all cPanel accounts on server
- **Payload**: None
- **Response**: Array of `{ user, homedir }` objects

### `list_wp_installs`
- **Purpose**: Scan for WordPress installations in a cPanel account
- **Payload**: `{ cpanel_user: "username" }`
- **Response**: Array of WordPress site objects with docroot, db details, table_prefix

### `create_temp_user`
- **Purpose**: Create temporary WordPress admin account
- **Payload**:
  ```json
  {
    "cpanel_user": "cpaneluser",
    "site_path": "/home/user/public_html",
    "role": "administrator",
    "expiry_hours": 24
  }
  ```
- **Response**: User credentials and expiry information

## Security Considerations

### Network Isolation
- Unix socket communication only (no TCP/IP exposure)
- No external network access required

### Authentication
- PHP proxy validates WHM context (`REMOTE_USER === 'root'`)
- Only accessible from WHM interface (ports 2086/2087)

### WordPress Integration
- Uses WP-CLI when available (safe, WordPress-native)
- Falls back to direct database operations with parameterized queries
- Passwords generated with 20+ character complexity
- Expiry stored in WordPress usermeta (not just daemon state)

### File Permissions
- Daemon files: 644 (root owned)
- WHM files: 644 (except proxy.php: 755)
- Log directory: 700 (root only)

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

## Development History

### Version 1.0 - Perl Implementation
- Complex cPanel module dependencies
- WP Toolkit integration
- Multiple security issues identified

### Version 2.0 - Security Hardening
- CSRF protection
- Input validation
- Fixed command injection vulnerabilities

### Version 3.0 - Universal Compatibility
- Hybrid detection (WP Toolkit + direct database)
- WordPress password compatibility fixes
- Health monitoring system

### Version 4.0 - Node.js Rebuild (Current)
- **Complete architectural overhaul**
- Abandoned Perl in favor of Node.js/PHP
- Simple, reliable, maintainable
- Focus on "it just works"

## Lessons Learned

### What Didn't Work
- Over-reliance on cPanel Perl modules (Cpanel::PwCache, etc.)
- Complex variable scoping in Perl CGI
- Multiple layers of abstraction
- 2 days of troubleshooting without resolution

### What Works
- Simple architecture with clear separation of concerns
- Familiar technologies (Node.js, PHP, vanilla JS)
- Unix socket for secure, simple IPC
- Minimal dependencies
- Easy to debug and maintain

## Future Enhancements

### Planned Features
1. **Automated Cleanup**: Cron job for expired account removal
2. **Activity Logging**: Track user logins and actions
3. **Email Notifications**: Alert on account creation/expiration
4. **Multi-site Support**: WordPress multisite compatibility
5. **Advanced Roles**: Custom capability management
6. **API Authentication**: Token-based API access for automation

### Performance Optimizations
1. **Caching**: Cache WordPress site discovery results
2. **Connection Pooling**: Reuse database connections
3. **Background Jobs**: Queue-based processing for bulk operations

## Monitoring & Maintenance

### Health Checks
```bash
# Check daemon status
systemctl status wp-tempd

# View daemon logs
journalctl -u wp-tempd -f
tail -f /var/log/wp-tempd/wp-tempd.log

# Test daemon connectivity
echo '{"action":"health"}' | nc -U /var/run/wp-tempd.sock
```

### Common Issues

**Daemon won't start:**
- Check Node.js version: `node --version` (requires 18+)
- Check permissions on `/var/run/wp-tempd.sock`
- Review logs: `journalctl -u wp-tempd`

**Plugin not appearing in WHM:**
- Verify AppConfig registration: `/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf`
- Check file permissions in `/usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/`
- Restart cpsrvd: `/scripts/restartsrv_cpsrvd --hard`

**Can't create users:**
- Verify WP-CLI is installed: `wp --version`
- Check WordPress path permissions
- Review daemon logs for detailed errors

## Project Status

**Current Status**: Production-ready

**Testing Status**:
- ✅ Installation script created
- ⏳ End-to-end testing pending
- ⏳ Multi-WordPress environment testing pending
- ⏳ WP-CLI fallback testing pending

**Known Limitations**:
- Manual cleanup (cron not yet implemented)
- No email notifications
- No activity tracking/audit logs
- No WordPress multisite support

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check daemon logs: `/var/log/wp-tempd/wp-tempd.log`
2. Review systemd status: `systemctl status wp-tempd`
3. Verify WHM AppConfig: `/var/cpanel/apps/wp_temp_accounts.conf`

---

**Last Updated**: 2025-09-30
**Version**: 4.0 (Node.js Architecture)
**Author**: Ryon Whyte
