#!/usr/local/cpanel/3rdparty/bin/php
<?php
/**
 * WordPress Temporary Accounts - cPanel Proxy
 * Forwards requests from cPanel users to the daemon
 */

header('Content-Type: application/json');

// Security: Only allow from cPanel context
if (!isset($_SERVER['REMOTE_USER']) || empty($_SERVER['REMOTE_USER'])) {
    respondError('not_cpanel', 'This must be called from cPanel');
}

// Get the logged-in cPanel user
$cpanelUser = $_SERVER['REMOTE_USER'];

// Validate request
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respondError('invalid_method', 'Only POST requests allowed');
}

// Read request body
$body = file_get_contents('php://input');
$request = json_decode($body, true);

if (!$request || !isset($request['action'])) {
    respondError('invalid_request', 'Invalid JSON or missing action');
}

// Inject the cPanel user into the payload for security
if (!isset($request['payload'])) {
    $request['payload'] = [];
}
$request['payload']['cpanel_user'] = $cpanelUser;

// Restrict actions for cPanel users
$allowedActions = ['health', 'list_wp_installs', 'create_temp_user'];
if (!in_array($request['action'], $allowedActions)) {
    respondError('forbidden_action', 'Action not allowed for cPanel users');
}

// Forward to Unix socket
$socket = @stream_socket_client(
    'unix:///var/run/wp-tempd.sock',
    $errno,
    $errstr,
    5
);

if (!$socket) {
    respondError('daemon_unreachable', "Cannot connect to daemon: $errstr");
}

fwrite($socket, json_encode($request));
$response = stream_get_contents($socket);
fclose($socket);

// Return response
echo $response;

function respondError($code, $message) {
    echo json_encode([
        'ok' => false,
        'error' => ['code' => $code, 'message' => $message]
    ]);
    exit;
}
