#!/bin/bash

echo "Clearing all cPanel caches..."

# Clear system-level caches
rm -rf /usr/local/cpanel/base/frontend/jupiter/.cpanelcache/* 2>/dev/null
rm -rf /usr/local/cpanel/base/frontend/paper_lantern/.cpanelcache/* 2>/dev/null

# Clear user-level caches for all users
for userdir in /home/*; do
    if [ -d "$userdir/.cpanel/caches" ]; then
        echo "Clearing cache for user: $(basename $userdir)"
        rm -rf "$userdir/.cpanel/caches/dynamicui/"* 2>/dev/null
    fi
done

# Clear root user cache
rm -rf /root/.cpanel/caches/dynamicui/* 2>/dev/null

# Rebuild sprites
/usr/local/cpanel/bin/rebuild_sprites 2>/dev/null || true

# Restart cPanel
/scripts/restartsrv_cpsrvd --hard

echo "All caches cleared and cPanel restarted!"
echo "Please log out and back into cPanel to see changes."