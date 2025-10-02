# Final Deployment Guide - Template Toolkit Version

## Summary of All Issues Fixed

### Issue #1: Visual Integration ✅
**Problem**: Plugin appeared as standalone page
**Solution**: Implemented Template Toolkit with `master_templates/master.tmpl` wrapper
**Result**: Plugin now integrates seamlessly with WHM interface

### Issue #2: JSON Request Errors ✅
**Problem**: "Invalid JSON request" on all API calls
**Solution**: Dual-mode POST body reading (POSTDATA + STDIN)
**Result**: API calls work correctly

### Issue #3: Raw HTML Rendering ✅
**Problem**: Browser showing HTML source code instead of rendering
**Solution**: Proper Template Toolkit implementation (not heredoc)
**Result**: HTML renders correctly with WHM master template

### Issue #4: Deprecated Theme Path ✅
**Problem**: Using Paper Lantern (deprecated)
**Solution**: Jupiter theme primary, Paper Lantern fallback
**Result**: Modern theme support

### Issue #5: Security & Compliance ✅
**Problem**: Missing input validation, no audit logs
**Solution**: Enterprise-grade validation and logging
**Result**: Production-ready security

---

## Architecture Overview

### Official cPanel Template Toolkit Implementation

```
WordPress Temporary Accounts Plugin
├── WHM Plugin (Administrators)
│   ├── CGI Script (Backend Logic)
│   │   └── /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi
│   ├── Template (Frontend UI)
│   │   └── /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/wp_temp_accounts.tmpl
│   └── Icon
│       └── /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts_icon.png
└── cPanel Plugin (Users)
    ├── CGI Script
    │   └── /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.cgi
    └── Icon
        └── /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/wp_temp_accounts_icon.png
```

---

## Template Toolkit Flow

```
User Request (GET)
     ↓
wp_temp_accounts.cgi (Perl)
     ↓
Cpanel::Template::process_template()
     ↓
Loads: wp_temp_accounts.tmpl
     ↓
Processes WRAPPER directive
     ↓
Loads: master_templates/master.tmpl
     ↓
Inserts plugin content
     ↓
Applies Bootstrap theme
     ↓
Processes locale.maketext() (localization)
     ↓
Renders complete HTML
     ↓
Browser receives integrated page
```

---

## Files in This Release

### Source Files (Development)
```
wordpress_temporary_accounts/
├── whm/
│   ├── wp_temp_accounts.cgi       (Backend CGI script)
│   └── wp_temp_accounts.tmpl      (Template Toolkit UI)
├── cpanel/
│   └── wp_temp_accounts.cgi       (cPanel user version)
├── packaging/
│   ├── wp_temp_accounts.conf      (WHM AppConfig)
│   ├── wp_temp_accounts_cpanel.conf (cPanel AppConfig)
│   └── wp_temp_accounts_icon.png  (48x48 PNG icon)
├── install.sh                     (Installation script)
├── uninstall.sh                   (Uninstallation script)
├── README.md                      (User documentation)
├── LICENSE                        (MIT License)
└── Documentation/
    ├── PRIORITY_FIXES.md
    ├── WHM_INTEGRATION_FIX.md
    ├── JSON_FIX.md
    ├── RENDERING_FIX.md
    ├── TEMPLATE_TOOLKIT_MIGRATION.md
    └── FINAL_DEPLOYMENT_GUIDE.md (this file)
```

### Installed Files (Production)
```
WHM Plugin:
  /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
    ├── wp_temp_accounts.cgi (755)
    └── wp_temp_accounts_icon.png (644)
  /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
    └── wp_temp_accounts.tmpl (644)
  /var/cpanel/apps/
    └── wp_temp_accounts.conf (644)

cPanel Plugin:
  /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/
    ├── index.cgi (755)
    └── wp_temp_accounts_icon.png (644)
  /usr/local/cpanel/base/frontend/paper_lantern/wp_temp_accounts/ (fallback)
    ├── index.cgi (755)
    └── wp_temp_accounts_icon.png (644)
  /var/cpanel/apps/
    └── wp_temp_accounts_cpanel.conf (644)

Logs:
  /var/log/wp_temp_accounts/
    ├── whm.log (640)
    └── cpanel.log (640)
```

---

## Pre-Deployment Checklist

### Server Requirements
- [ ] cPanel/WHM installed (version 100+)
- [ ] Root SSH access
- [ ] WP-CLI installed on server
- [ ] Perl 5.10+ (included with cPanel)
- [ ] Template Toolkit module (included with cPanel)

### Files Ready
- [ ] All files transferred to `/root/wordpress_temporary_accounts/`
- [ ] File permissions correct (755 for scripts)
- [ ] No Git metadata (`.git/` removed)

---

## Installation Steps

### 1. Transfer Files to Server

```bash
# From your local machine
cd /home/ryon-whyte/Documents/GitHub
tar czf wordpress_temporary_accounts.tar.gz wordpress_temporary_accounts/
scp wordpress_temporary_accounts.tar.gz root@your-server:/root/

# On the server
ssh root@your-server
cd /root
tar xzf wordpress_temporary_accounts.tar.gz
cd wordpress_temporary_accounts
```

### 2. Verify File Structure

```bash
ls -la
# Should show:
# - install.sh
# - uninstall.sh
# - whm/ directory
# - cpanel/ directory
# - packaging/ directory
```

### 3. Run Uninstaller (if upgrading)

```bash
./uninstall.sh
```

**Expected Output**:
```
======================================
 WordPress Temporary Accounts
 Uninstallation
======================================

This will remove:
  • WHM plugin
  • cPanel plugin
  • All AppConfigs
  • All plugin files

Continue? (y/n) y

[✓] Unregistering from WHM...
[✓] Unregistering from cPanel...
[✓] Removing AppConfigs...
[✓] Removing WHM files...
[✓] Removing cPanel files...
[✓] Removing log directory...
[✓] Verifying removal...
[✓] All files removed successfully
[✓] Restarting cpsrvd...

======================================
Uninstallation Complete!
======================================
```

### 4. Run Installer

```bash
./install.sh
```

**Expected Output**:
```
======================================
 WordPress Temporary Accounts
 Pure Perl Installation (WHM + cPanel)
======================================

[✓] Creating directories...
[✓] Installing WHM plugin...
[✓] Installing WHM template...
[✓] Installing cPanel plugin...
[✓] Registering with WHM...
[✓] AppConfig created successfully
[✓] WHM plugin registered successfully
[✓] Registering with cPanel...
[✓] cPanel plugin registered successfully
[✓] Setting file permissions...
[✓] Restarting cpsrvd...

======================================
Installation Complete!
======================================

Access the plugin:
  WHM: WHM → Plugins → WordPress Temporary Accounts
  cPanel: cPanel → Software → WordPress Temporary Accounts
```

### 5. Verify Installation

```bash
# Check WHM CGI
ls -la /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
# Should show:
# -rwxr-xr-x wp_temp_accounts.cgi
# -rw-r--r-- wp_temp_accounts_icon.png

# Check WHM Template
ls -la /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
# Should show:
# -rw-r--r-- wp_temp_accounts.tmpl

# Check AppConfig
cat /var/cpanel/apps/wp_temp_accounts.conf
# Should show valid AppConfig

# Check cPanel Plugin
ls -la /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/
# Should show:
# -rwxr-xr-x index.cgi
# -rw-r--r-- wp_temp_accounts_icon.png

# Check Logs Directory
ls -la /var/log/wp_temp_accounts/
# Should show empty directory with 750 permissions
```

---

## Post-Installation Testing

### Test 1: WHM Access

1. **Navigate**: WHM → Plugins → WordPress Temporary Accounts

2. **Visual Check**:
   - [ ] WHM header visible (logo, navigation)
   - [ ] WHM sidebar menu accessible
   - [ ] Breadcrumb: Home → Plugins → WordPress Temporary Accounts
   - [ ] Plugin content appears in main area
   - [ ] Bootstrap styling applied
   - [ ] "System: OK" badge shows in green
   - [ ] NO raw HTML visible

3. **Functional Check**:
   - [ ] Account dropdown populates
   - [ ] "Scan for WordPress" button works
   - [ ] WordPress sites detected
   - [ ] Forms display correctly
   - [ ] No JavaScript errors in console

### Test 2: cPanel Access

1. **Navigate**: cPanel → Software → WordPress Temporary Accounts

2. **Visual Check**:
   - [ ] cPanel header visible
   - [ ] Plugin integrated (not standalone)
   - [ ] "System: OK" badge shows
   - [ ] Forms display correctly

3. **Functional Check**:
   - [ ] Only current user's sites shown
   - [ ] WordPress detection works
   - [ ] User creation works
   - [ ] User deletion works

### Test 3: API Calls

**Open Browser Console** (F12):

```javascript
// Should see successful responses
{ok: true, data: {...}}
```

**Check for errors**:
- [ ] No "Invalid JSON request"
- [ ] No 404 errors
- [ ] No Perl errors
- [ ] Responses are proper JSON

### Test 4: Complete Workflow

1. **Select Account**: Choose a cPanel account
2. **Scan WordPress**: Click "Scan for WordPress"
3. **Select Site**: Choose a WordPress installation
4. **Load Users**: Click "Load Users"
5. **Create User**:
   - Username: `temp_test_123`
   - Email: `temp@example.com`
   - Days: `7`
   - Click "Create Temporary User"
6. **Verify**:
   - [ ] Success message appears
   - [ ] User appears in table
   - [ ] Password displayed
   - [ ] Expiration date shown
7. **Delete User**: Click "Delete" button
8. **Verify**: User removed from table

### Test 5: Audit Logs

```bash
# Watch logs in real-time
tail -f /var/log/wp_temp_accounts/*.log
```

**Perform actions and verify logging**:
```
[Wed Jan  1 12:34:56 2025] CREATE_USER_SUCCESS | user=temp_test_123 site=/home/user/public_html days=7 | success | 192.168.1.100
[Wed Jan  1 12:35:12 2025] DELETE_USER_SUCCESS | user=temp_test_123 site=/home/user/public_html | success | 192.168.1.100
```

---

## Troubleshooting

### Issue: Plugin Not in WHM Menu

**Check AppConfig registration**:
```bash
/usr/local/cpanel/bin/unregister_appconfig wp_temp_accounts
/usr/local/cpanel/bin/register_appconfig /var/cpanel/apps/wp_temp_accounts.conf
/scripts/restartsrv_cpsrvd --hard
```

**Verify AppConfig**:
```bash
cat /var/cpanel/apps/wp_temp_accounts.conf
# Should contain:
# name=wp_temp_accounts
# service=whostmgr
# user=root
# acls=all
```

### Issue: Template Not Found

**Error**: "Can't locate template file"

**Check**:
```bash
ls -la /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
```

**Fix**:
```bash
cd /root/wordpress_temporary_accounts
mkdir -p /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
install -m 644 whm/wp_temp_accounts.tmpl /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
```

### Issue: Permission Denied

**Error**: "Permission denied" when accessing plugin

**Fix**:
```bash
chmod 755 /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/wp_temp_accounts.cgi
chmod 644 /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/wp_temp_accounts.tmpl
chown -R root:root /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts
chown -R root:root /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
```

### Issue: JSON Errors Still Appearing

**Check error logs**:
```bash
tail -f /usr/local/cpanel/logs/error_log
```

**Test API directly**:
```bash
curl -X POST https://your-server:2087/cgi/wp_temp_accounts/wp_temp_accounts.cgi \
  -H "Content-Type: application/json" \
  -d '{"action":"health","payload":{}}' \
  -u root:your-password \
  -k
```

**Expected**:
```json
{"ok":true,"data":{"status":"ok","uptime_sec":12345}}
```

### Issue: WP-CLI Not Found

**Install WP-CLI**:
```bash
curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
mv wp-cli.phar /usr/local/bin/wp
wp --info
```

---

## Monitoring & Maintenance

### Log Rotation

Create `/etc/logrotate.d/wp_temp_accounts`:
```
/var/log/wp_temp_accounts/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 640 root root
}
```

### Regular Checks

**Weekly**:
```bash
# Check log size
du -sh /var/log/wp_temp_accounts/

# Check for errors
grep -i error /var/log/wp_temp_accounts/*.log

# Verify permissions
ls -la /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/
ls -la /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
```

**Monthly**:
```bash
# Audit temporary users across all sites
# (Create custom script if needed)

# Review audit logs
tail -100 /var/log/wp_temp_accounts/whm.log
```

---

## Uninstallation

### Complete Removal

```bash
cd /root/wordpress_temporary_accounts
./uninstall.sh
```

**Verifies complete removal of**:
- WHM plugin files (CGI + template)
- cPanel plugin files (both Jupiter + Paper Lantern)
- AppConfig files
- Log directory
- All registrations

---

## Support & Documentation

### Documentation Files

- **README.md**: User guide and features
- **PRIORITY_FIXES.md**: Security improvements
- **WHM_INTEGRATION_FIX.md**: Template integration details
- **JSON_FIX.md**: Request handling details
- **RENDERING_FIX.md**: HTML rendering fix
- **TEMPLATE_TOOLKIT_MIGRATION.md**: TT implementation
- **FINAL_DEPLOYMENT_GUIDE.md**: This file

### Official Resources

- cPanel/WHM API Docs: https://api.docs.cpanel.net
- Template Toolkit Guide: https://api.docs.cpanel.net/guides/guide-to-template-toolkit/
- WHM Plugin Guide: https://api.docs.cpanel.net/guides/guide-to-whm-plugins/
- Style Guide: https://styleguide.cpanel.net

---

## Success Criteria

✅ **Installation**: All files installed, permissions correct
✅ **WHM Integration**: Plugin appears in WHM → Plugins menu
✅ **Visual**: Template renders with WHM header/navigation
✅ **Bootstrap**: Styling applied correctly
✅ **API**: JSON calls work without errors
✅ **WordPress**: Sites detected and users created
✅ **Logging**: All actions logged to audit files
✅ **Security**: Input validation working
✅ **cPanel**: User plugin works separately

---

## Final Status

**Version**: 5.0 (Template Toolkit Release)
**Status**: ✅ Production Ready
**Method**: Official cPanel Template Toolkit Implementation
**Integration**: Full WHM/cPanel Integration
**Security**: Enterprise-Grade
**Compatibility**: cPanel 100+, WHM, Jupiter Theme

**Ready for deployment!**
