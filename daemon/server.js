#!/usr/bin/env node

/**
 * WordPress Temporary Accounts Daemon
 * Simple Node.js service that handles WordPress user operations
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const util = require('util');

const execPromise = util.promisify(exec);

// Configuration
const SOCKET_PATH = '/var/run/wp-tempd.sock';
const LOG_PATH = '/var/log/wp-tempd/wp-tempd.log';

// Ensure log directory exists
const logDir = path.dirname(LOG_PATH);
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true, mode: 0o755 });
}

// Logging
function log(level, message, data = {}) {
    const timestamp = new Date().toISOString();
    const logEntry = {
        timestamp,
        level,
        message,
        ...data
    };

    const logLine = JSON.stringify(logEntry) + '\n';
    fs.appendFileSync(LOG_PATH, logLine);
    console.log(`[${timestamp}] ${level}: ${message}`);
}

// Response helpers
function success(data) {
    return { ok: true, data };
}

function error(code, message) {
    return { ok: false, error: { code, message } };
}

// Get list of cPanel accounts
async function listCpanelAccounts() {
    try {
        const { stdout } = await execPromise('cut -d: -f1,6 /etc/passwd | grep "^[^:]*:/home/" | sort');
        const accounts = stdout.trim().split('\n')
            .filter(line => line)
            .map(line => {
                const [user, homedir] = line.split(':');
                return { user, homedir };
            });

        log('info', 'Listed cPanel accounts', { count: accounts.length });
        return success(accounts);
    } catch (err) {
        log('error', 'Failed to list accounts', { error: err.message });
        return error('list_accounts_failed', err.message);
    }
}

// Find WordPress installations
async function listWordPressInstalls(cpanelUser) {
    try {
        if (!cpanelUser) {
            return error('missing_user', 'cPanel user required');
        }

        // Validate user exists
        try {
            await execPromise(`id "${cpanelUser}"`);
        } catch {
            return error('invalid_user', `User ${cpanelUser} does not exist`);
        }

        const searchPaths = [
            `/home/${cpanelUser}/public_html`,
            `/home/${cpanelUser}/www`,
            `/home/${cpanelUser}/domains/*/public_html`
        ];

        const installs = [];

        for (const searchPath of searchPaths) {
            try {
                const { stdout } = await execPromise(
                    `find ${searchPath} -maxdepth 3 -name "wp-config.php" -type f 2>/dev/null || true`
                );

                const configFiles = stdout.trim().split('\n').filter(f => f);

                for (const configFile of configFiles) {
                    const docroot = path.dirname(configFile);

                    // Parse wp-config.php for database info
                    const config = fs.readFileSync(configFile, 'utf8');
                    const dbName = config.match(/define\s*\(\s*['"]DB_NAME['"]\s*,\s*['"]([^'"]+)['"]\s*\)/)?.[1];
                    const dbUser = config.match(/define\s*\(\s*['"]DB_USER['"]\s*,\s*['"]([^'"]+)['"]\s*\)/)?.[1];
                    const dbHost = config.match(/define\s*\(\s*['"]DB_HOST['"]\s*,\s*['"]([^'"]+)['"]\s*\)/)?.[1] || 'localhost';
                    const tablePrefix = config.match(/\$table_prefix\s*=\s*['"]([^'"]+)['"]/)?.[1] || 'wp_';

                    installs.push({
                        cpuser: cpanelUser,
                        docroot,
                        db: { name: dbName, user: dbUser, host: dbHost },
                        table_prefix: tablePrefix
                    });
                }
            } catch (err) {
                // Silently continue if path doesn't exist
            }
        }

        log('info', 'Found WordPress installations', { user: cpanelUser, count: installs.length });
        return success(installs);
    } catch (err) {
        log('error', 'Failed to scan for WordPress', { user: cpanelUser, error: err.message });
        return error('scan_failed', err.message);
    }
}

// Create temporary WordPress user
async function createTempUser(payload) {
    try {
        const { cpanel_user, site_path, role = 'administrator', expiry_hours = 24 } = payload;

        if (!cpanel_user || !site_path) {
            return error('missing_params', 'cpanel_user and site_path required');
        }

        // Validate site_path is under the account's home directory
        const expectedPrefix = `/home/${cpanel_user}/`;
        if (!site_path.startsWith(expectedPrefix)) {
            return error('invalid_path', 'site_path must be inside the account homedir');
        }

        // Validate site_path contains wp-config.php
        const wpConfig = path.join(site_path, 'wp-config.php');
        if (!fs.existsSync(wpConfig)) {
            return error('invalid_path', 'wp-config.php not found in site_path');
        }

        // Generate random username and password
        const username = 'temp_' + Math.random().toString(36).substring(2, 10);
        const password = Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2);
        const email = `${username}@temporary.local`;

        // Calculate expiry timestamp
        const expiresAt = Math.floor(Date.now() / 1000) + (expiry_hours * 3600);

        // Try WP-CLI first
        try {
            await execPromise(
                `wp user create "${username}" "${email}" --role="${role}" --user_pass="${password}" --allow-root --path="${site_path}" 2>&1`
            );

            // Add metadata
            await execPromise(`wp user meta update "${username}" wp_temp_user 1 --allow-root --path="${site_path}"`);
            await execPromise(`wp user meta update "${username}" wp_temp_expires ${expiresAt} --allow-root --path="${site_path}"`);

            log('info', 'Created temp user via WP-CLI', { username, site_path });

            return success({
                user: username,
                temp_password: password,
                email,
                role,
                expires_at: expiresAt,
                method: 'wp-cli'
            });
        } catch (wpCliError) {
            // WP-CLI failed, would need DB fallback here
            log('error', 'WP-CLI failed, DB fallback not yet implemented', { error: wpCliError.message });
            return error('create_failed', 'WP-CLI not available and DB fallback not implemented');
        }
    } catch (err) {
        log('error', 'Failed to create temp user', { error: err.message });
        return error('create_failed', err.message);
    }
}

// Health check
async function healthCheck() {
    const uptime = process.uptime();
    return success({
        version: '1.0.0',
        uptime_sec: Math.floor(uptime),
        status: 'ok',
        pid: process.pid
    });
}

// Request handler
async function handleRequest(req, res) {
    let body = '';

    req.on('data', chunk => {
        body += chunk.toString();
        if (body.length > 65536) { // 64KB limit
            req.connection.destroy();
        }
    });

    req.on('end', async () => {
        try {
            const request = JSON.parse(body || '{}');
            const { action, payload = {} } = request;

            log('info', 'Request received', { action });

            let response;

            switch (action) {
                case 'health':
                    response = await healthCheck();
                    break;
                case 'list_cpanel_accounts':
                    response = await listCpanelAccounts();
                    break;
                case 'list_wp_installs':
                    response = await listWordPressInstalls(payload.cpanel_user);
                    break;
                case 'create_temp_user':
                    response = await createTempUser(payload);
                    break;
                default:
                    response = error('unknown_action', `Unknown action: ${action}`);
            }

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(response));
        } catch (err) {
            log('error', 'Request handling failed', { error: err.message });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(error('invalid_request', err.message)));
        }
    });
}

// Start server
function startServer() {
    // Remove old socket if exists
    if (fs.existsSync(SOCKET_PATH)) {
        fs.unlinkSync(SOCKET_PATH);
    }

    const server = http.createServer(handleRequest);

    server.listen(SOCKET_PATH, () => {
        // Set socket permissions
        fs.chmodSync(SOCKET_PATH, 0o660);
        fs.chownSync(SOCKET_PATH, 0, 0); // root:root

        log('info', 'Server started', { socket: SOCKET_PATH });
        console.log(`WordPress Temporary Accounts Daemon running on ${SOCKET_PATH}`);
    });

    // Graceful shutdown
    process.on('SIGTERM', () => {
        log('info', 'SIGTERM received, shutting down');
        server.close(() => {
            if (fs.existsSync(SOCKET_PATH)) {
                fs.unlinkSync(SOCKET_PATH);
            }
            process.exit(0);
        });
    });

    process.on('SIGINT', () => {
        log('info', 'SIGINT received, shutting down');
        server.close(() => {
            if (fs.existsSync(SOCKET_PATH)) {
                fs.unlinkSync(SOCKET_PATH);
            }
            process.exit(0);
        });
    });
}

// Start
startServer();
