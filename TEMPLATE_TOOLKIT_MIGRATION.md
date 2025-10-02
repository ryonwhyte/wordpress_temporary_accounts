# Template Toolkit Migration - Official cPanel Method

## What Changed

Migrated from `Whostmgr::HTMLInterface` to **Template Toolkit** - the official cPanel recommended approach for WHM plugins.

---

## Why This Change?

### Previous Approach (HTMLInterface)
```perl
use Whostmgr::HTMLInterface();
Whostmgr::HTMLInterface::defheader(...);
print <<'HTML';
... content ...
HTML
Whostmgr::HTMLInterface::deffooter();
```

**Issues**:
- ❌ Not the official recommended method
- ❌ Raw HTML in heredoc prone to rendering issues
- ❌ No internationalization support
- ❌ Difficult to maintain

### New Approach (Template Toolkit)
```perl
use Cpanel::Template ();
Cpanel::Template::process_template(
    'whostmgr',
    {
        'template_file' => 'wp_temp_accounts/wp_temp_accounts.tmpl',
        'print'         => 1,
    }
);
```

**Benefits**:
- ✅ **Official cPanel method** (documented at api.docs.cpanel.net)
- ✅ **Proper WHM integration** using master templates
- ✅ **Localization support** with `locale.maketext()`
- ✅ **Bootstrap framework** built-in
- ✅ **Cleaner code** separation (logic vs presentation)

---

## File Structure

### New Files Created

**1. `whm/wp_temp_accounts.tmpl`** - Template Toolkit template
- Location after install: `/usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/wp_temp_accounts.tmpl`
- Uses WHM master template wrapper
- Includes localization
- Bootstrap-compatible markup

### Modified Files

**2. `whm/wp_temp_accounts.cgi`** - Updated to use templates
- Changed `render_ui()` function to call `Cpanel::Template::process_template()`
- Old heredoc code disabled but kept for reference
- API handling unchanged

**3. `install.sh`** - Copies template file
- Creates `/usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/`
- Installs `.tmpl` file with 644 permissions

**4. `uninstall.sh`** - Removes template directory
- Cleans up template directory completely

---

## Template Structure

### Template File (`wp_temp_accounts.tmpl`)

```perl
[%
USE Whostmgr;
USE JSON;

# Handle RTL locales
IF locale.get_html_dir_attr() == 'rtl';
    SET rtl_bootstrap = Whostmgr.find_file_url('/3rdparty/bootstrap-rtl/...');
END;

# Wrap with WHM master template
WRAPPER 'master_templates/master.tmpl'
    header = locale.maketext("WordPress Temporary Accounts")
    theme='bootstrap';
%]

<!-- Your plugin HTML here -->
<div class="container">
    <h2>[% locale.maketext("WordPress Temporary Accounts") %]</h2>
    ...
</div>

[% END %]
```

### Key Features

1. **Master Template Wrapper**
   - Automatically includes WHM header/navigation
   - Adds footer
   - Loads Bootstrap CSS/JS
   - Handles theme integration

2. **Localization**
   ```perl
   [% locale.maketext("Text to translate") %]
   ```
   - Automatic translation support
   - RTL language support

3. **Bootstrap Framework**
   ```html
   <div class="row">
       <div class="col-xs-12">
           <button class="btn btn-primary">Click</button>
       </div>
   </div>
   ```
   - Responsive grid system
   - Pre-styled components
   - WHM-consistent design

4. **JavaScript Integration**
   - Same JavaScript code as before
   - API calls unchanged
   - Works with template markup

---

## CGI Script Changes

### Old render_ui() Function
```perl
sub render_ui {
    use Whostmgr::HTMLInterface();

    Whostmgr::HTMLInterface::defheader(...);

    print <<'HTML';
    <style>...</style>
    <div>...</div>
    HTML

    Whostmgr::HTMLInterface::deffooter();
}
```

### New render_ui() Function
```perl
sub render_ui {
    use Cpanel::Template ();

    print "Content-type: text/html\r\n\r\n";

    Cpanel::Template::process_template(
        'whostmgr',
        {
            'template_file' => 'wp_temp_accounts/wp_temp_accounts.tmpl',
            'print'         => 1,
        }
    );

    return;
}
```

**What it does**:
1. Prints HTTP header
2. Tells Template Toolkit to process our template
3. `'whostmgr'` = use WHM template directory
4. `'print' => 1` = output directly to browser
5. Template system handles the rest

---

## Installation

### Files Installed

```
/usr/local/cpanel/whostmgr/docroot/
├── cgi/wp_temp_accounts/
│   ├── wp_temp_accounts.cgi          (755)
│   └── wp_temp_accounts_icon.png     (644)
└── templates/wp_temp_accounts/
    └── wp_temp_accounts.tmpl          (644)
```

### Installation Script Updates

**Added** (`install.sh` line 51-54):
```bash
# Install WHM template
log_info "Installing WHM template..."
mkdir -p /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
install -m 644 whm/wp_temp_accounts.tmpl /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
```

### Uninstallation Script Updates

**Added** (`uninstall.sh` line 65):
```bash
rm -rf /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts
```

---

## Advantages of Template Toolkit

### 1. **Official cPanel Method**
- Documented in official guides
- Used by cPanel's own plugins
- Future-proof compatibility

### 2. **Proper WHM Integration**
- Automatic header/footer
- Consistent navigation
- Theme support
- Mobile responsive

### 3. **Internationalization**
- Built-in translation support
- RTL language handling
- Locale-aware formatting

### 4. **Maintainability**
- Separate logic (CGI) from presentation (template)
- Easier to update UI
- Reusable components

### 5. **Bootstrap Framework**
- Professional appearance
- Responsive design
- Consistent with WHM
- Pre-built components

---

## Comparison: Before vs After

### Before (HTMLInterface)
```
Browser Request
     ↓
CGI Script executes
     ↓
defheader() outputs HTML header
     ↓
Perl heredoc prints content
     ↓
deffooter() outputs HTML footer
     ↓
Browser receives complete HTML
```

**Issues**: Heredoc indentation, no localization, manual HTML

### After (Template Toolkit)
```
Browser Request
     ↓
CGI Script executes
     ↓
Cpanel::Template loads .tmpl file
     ↓
Template processes WRAPPER directive
     ↓
master.tmpl renders header/footer
     ↓
Plugin template content inserted
     ↓
Localization applied
     ↓
Browser receives complete HTML
```

**Benefits**: Clean separation, automatic integration, localization

---

## Testing Checklist

After deployment:

### Visual Integration
- [ ] WHM header/navigation visible
- [ ] Plugin appears in content area (not standalone)
- [ ] Bootstrap styling applied
- [ ] Responsive on mobile
- [ ] No raw HTML visible

### Functionality
- [ ] JavaScript loads correctly
- [ ] API calls work
- [ ] Forms submit properly
- [ ] User interaction works

### Browser Console
- [ ] No 404 errors for templates
- [ ] No JavaScript errors
- [ ] API responses correct

### Localization (if testing)
- [ ] Text wrapped in `locale.maketext()` translates
- [ ] RTL languages display correctly
- [ ] Date/time formatting locale-aware

---

## Troubleshooting

### Error: "Template not found"

**Check**:
```bash
ls -la /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/
```

**Should show**:
```
-rw-r--r-- 1 root root ... wp_temp_accounts.tmpl
```

**Fix**:
```bash
cd /root/wordpress_temporary_accounts
./install.sh
```

### Error: "Can't locate Cpanel/Template.pm"

**Cause**: Not on a cPanel server

**Solution**: Only deployable on cPanel/WHM servers

### Still Shows Raw HTML

**Check**: Old code disabled
```perl
print <<'HTML_DISABLED';  ← Should say DISABLED
```

**Check**: Template being processed
```bash
tail -f /usr/local/cpanel/logs/error_log
# Look for template processing messages
```

---

## Migration Summary

✅ **Created**: `whm/wp_temp_accounts.tmpl` (Template Toolkit file)
✅ **Updated**: `whm/wp_temp_accounts.cgi` (Uses Cpanel::Template)
✅ **Updated**: `install.sh` (Installs template)
✅ **Updated**: `uninstall.sh` (Removes template)
✅ **Disabled**: Old heredoc HTML (kept for reference)

---

## Deployment

```bash
cd /root/wordpress_temporary_accounts
./uninstall.sh  # Remove old version
./install.sh    # Install new version with templates
```

**Access**:
WHM → Plugins → WordPress Temporary Accounts

**Expected Result**:
- ✅ Properly integrated WHM interface
- ✅ Bootstrap-styled components
- ✅ Working API calls
- ✅ Professional appearance matching WHM

---

**Status**: ✅ Official cPanel Template Toolkit implementation complete!
