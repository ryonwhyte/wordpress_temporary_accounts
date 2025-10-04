#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Full WordPress Temp Accounts Debug ===${NC}\n"

echo -e "${GREEN}1. Checking file installation:${NC}"
echo "----------------------------------------"
echo "WHM files:"
ls -la /usr/local/cpanel/whostmgr/docroot/cgi/wp_temp_accounts/ 2>/dev/null || echo "  WHM CGI directory not found"
ls -la /usr/local/cpanel/whostmgr/docroot/templates/wp_temp_accounts/ 2>/dev/null || echo "  WHM template directory not found"
ls -la /usr/local/cpanel/whostmgr/docroot/addon_plugins/wp_temp_accounts_icon.png 2>/dev/null || echo "  WHM icon not found"

echo -e "\ncPanel files (Jupiter):"
ls -la /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/ 2>/dev/null || echo "  Jupiter plugin directory not found"

echo -e "\ncPanel files (3rdparty):"
ls -la /usr/local/cpanel/base/3rdparty/wp_temp_accounts/ 2>/dev/null || echo "  3rdparty directory not found"

echo -e "\n${GREEN}2. Checking dynamicui configuration:${NC}"
echo "----------------------------------------"
echo "Looking for dynamicui files:"
find /usr/local/cpanel/base/frontend/jupiter/dynamicui/ -name "*wp*" -o -name "*wordpress*" 2>/dev/null | while read file; do
    echo "Found: $file"
    echo "Content preview:"
    head -20 "$file" 2>/dev/null | sed 's/^/  /'
done

if [ ! -f "/usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wp_temp_accounts.conf" ]; then
    echo -e "${RED}dynamicui_wp_temp_accounts.conf NOT FOUND!${NC}"
else
    echo -e "${GREEN}dynamicui_wp_temp_accounts.conf exists${NC}"
fi

echo -e "\n${GREEN}3. Checking if plugin appears in dynamicui:${NC}"
echo "----------------------------------------"
# Check the main dynamicui.conf file
if [ -f "/usr/local/cpanel/base/frontend/jupiter/dynamicui.conf" ]; then
    echo "Checking main dynamicui.conf for our plugin:"
    grep -E "wp_temp_accounts|wordpress_tools" /usr/local/cpanel/base/frontend/jupiter/dynamicui.conf 2>/dev/null || echo "  Not found in main config"
fi

echo -e "\n${GREEN}4. Checking AppConfig registration:${NC}"
echo "----------------------------------------"
ls -la /var/cpanel/apps/ | grep wp_temp
cat /var/cpanel/apps/wp_temp_accounts.conf 2>/dev/null || echo "WHM AppConfig not found"

echo -e "\n${GREEN}5. Checking for errors in logs:${NC}"
echo "----------------------------------------"
echo "Recent cPanel errors:"
tail -50 /usr/local/cpanel/logs/error_log 2>/dev/null | grep -v "favicon" || echo "  No recent errors or cannot read log"

echo -e "\nAccess log entries:"
grep "wp_temp_accounts" /usr/local/cpanel/logs/access_log 2>/dev/null | tail -5 || echo "  No access log entries found"

echo -e "\n${GREEN}6. Checking cPanel cache status:${NC}"
echo "----------------------------------------"
if [ -d "/usr/local/cpanel/base/frontend/jupiter/.cpanelcache" ]; then
    count=$(ls -1 /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/ 2>/dev/null | wc -l)
    echo "Cache files present: $count"
    if [ $count -gt 0 ]; then
        echo -e "${YELLOW}Cache exists - may need clearing${NC}"
    fi
else
    echo "Cache directory doesn't exist"
fi

echo -e "\n${GREEN}7. Checking theme and version:${NC}"
echo "----------------------------------------"
/usr/local/cpanel/cpanel -V 2>/dev/null || echo "Cannot determine cPanel version"

echo -e "\n${GREEN}8. Testing direct file access:${NC}"
echo "----------------------------------------"
echo "Test if index.live.pl is executable:"
if [ -x "/usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.live.pl" ]; then
    echo -e "${GREEN}✓ index.live.pl is executable${NC}"
    echo "First few lines:"
    head -5 /usr/local/cpanel/base/frontend/jupiter/wp_temp_accounts/index.live.pl
else
    echo -e "${RED}✗ index.live.pl is not executable or doesn't exist${NC}"
fi

echo -e "\n${GREEN}9. Checking for duplicate or conflicting entries:${NC}"
echo "----------------------------------------"
echo "All dynamicui files mentioning wordpress:"
grep -l -i wordpress /usr/local/cpanel/base/frontend/jupiter/dynamicui/* 2>/dev/null

echo -e "\n${GREEN}10. Verifying YAML format of dynamicui:${NC}"
echo "----------------------------------------"
if [ -f "/usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wp_temp_accounts.conf" ]; then
    echo "Checking YAML syntax:"
    python3 -c "import yaml; yaml.safe_load(open('/usr/local/cpanel/base/frontend/jupiter/dynamicui/dynamicui_wp_temp_accounts.conf'))" 2>&1 && echo -e "${GREEN}✓ Valid YAML${NC}" || echo -e "${RED}✗ Invalid YAML${NC}"
fi

echo -e "\n${YELLOW}=== Summary ===${NC}"
echo "----------------------------------------"
echo "Run this after installation to see what's wrong."
echo "If the dynamicui file exists but plugin doesn't show:"
echo "  1. The YAML format might be wrong"
echo "  2. The icon paths might be incorrect"
echo "  3. Cache needs clearing"
echo "  4. cPanel service needs restart"
echo ""
echo "Direct test URLs:"
echo "  Icon: https://server.sitepact.net:2083/frontend/jupiter/wp_temp_accounts/wp_temp_accounts.svg"
echo "  Plugin: https://server.sitepact.net:2083/frontend/jupiter/wp_temp_accounts/index.live.pl"