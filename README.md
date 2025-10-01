# WordPress Temporary Accounts WHM/cPanel Plugin

A simple, reliable plugin for creating temporary WordPress administrator accounts. Works in both **WHM** (for administrators) and **cPanel** (for individual users).

## Architecture

- **Backend**: Node.js daemon (simple, fast, reliable)
- **Proxy**: PHP CGI (minimal, works with both WHM and cPanel)
- **Frontend**: HTML/CSS/JavaScript (clean, modern)
- **Security**: Unix socket (no network exposure)

## Features

- ✅ Create temporary WP admin accounts
- ✅ Automatic expiration and cleanup
- ✅ Works with any WordPress installation
- ✅ **Dual access**: WHM (all accounts) and cPanel (per-user)
- ✅ No complex dependencies
- ✅ Simple to install and maintain

## Access

- **WHM Users**: WHM → Plugins → WordPress Temporary Accounts (manage all sites)
- **cPanel Users**: cPanel → Software → WordPress Temporary Accounts (manage own sites)

## Installation

```bash
cd wordpress_temporary_accounts
chmod +x install.sh
./install.sh
```

## Technology Stack

- **Node.js 18+** - Backend daemon
- **PHP 7.4+** - Proxy layer (WHM and cPanel)
- **systemd** - Service management
- **WP-CLI** - WordPress operations (with DB fallback)

## Directory Structure

```
wordpress_temporary_accounts/
├── daemon/          # Node.js backend
├── whm/            # WHM integration (administrators)
├── cpanel/         # cPanel integration (users)
├── packaging/      # Service files, AppConfigs, icon
├── install.sh      # Installation script
├── uninstall.sh    # Uninstallation script
└── README.md       # This file
```

## License

MIT License
