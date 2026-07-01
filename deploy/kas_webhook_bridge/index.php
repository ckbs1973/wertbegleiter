<?php
declare(strict_types=1);

/*
 * WertBegleiter Kapitalmarkt KAS webhook bridge.
 *
 * This endpoint accepts TradingView webhook facts and stores them for local
 * polling. It does not execute orders, does not call a broker and does not
 * create trading recommendations.
 */

function wb_json(array $payload, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function wb_load_config(): array
{
    $path = __DIR__ . '/config.php';
    if (!is_file($path)) {
        wb_json(array(
            'status' => 'configuration_missing',
            'error' => 'config.php fehlt. config.example.php kopieren und Token setzen.',
            'information_only' => true,
        ), 500);
    }
    $config = require $path;
    if (!is_array($config)) {
        wb_json(array('status' => 'configuration_invalid', 'information_only' => true), 500);
    }
    $token = trim((string)($config['token'] ?? ''));
    if (strlen($token) < 24) {
        wb_json(array(
            'status' => 'configuration_invalid',
            'error' => 'token muss mindestens 24 Zeichen lang sein.',
            'information_only' => true,
        ), 500);
    }
    $config['storage_dir'] = (string)($config['storage_dir'] ?? (__DIR__ . '/storage'));
    $config['max_body_bytes'] = (int)($config['max_body_bytes'] ?? 262144);
    return $config;
}

function wb_path_route(): array
{
    $token = isset($_GET['token']) ? (string)$_GET['token'] : '';
    $kind = isset($_GET['kind']) ? (string)$_GET['kind'] : '';
    if ($token !== '' && $kind !== '') {
        return array($token, $kind);
    }

    $path = parse_url((string)($_SERVER['REQUEST_URI'] ?? ''), PHP_URL_PATH);
    $parts = explode('/', trim((string)$path, '/'));
    $count = count($parts);
    for ($idx = 0; $idx < $count; $idx++) {
        if ($parts[$idx] === 'tv' && isset($parts[$idx + 1], $parts[$idx + 2])) {
            return array($parts[$idx + 1], $parts[$idx + 2]);
        }
    }
    return array('', '');
}

function wb_storage_dir(array $config): string
{
    $dir = rtrim((string)$config['storage_dir'], '/');
    if (!is_dir($dir) && !mkdir($dir, 0750, true)) {
        wb_json(array('status' => 'storage_error', 'error' => 'storage_dir konnte nicht erstellt werden.', 'information_only' => true), 500);
    }
    $deny = $dir . '/.htaccess';
    if (!is_file($deny)) {
        @file_put_contents($deny, "Require all denied\n");
    }
    return $dir;
}

function wb_read_json_body(int $maxBytes): array
{
    $length = (int)($_SERVER['CONTENT_LENGTH'] ?? 0);
    if ($length <= 0) {
        wb_json(array('status' => 'invalid_payload', 'error' => 'Leerer Request Body.', 'information_only' => true), 400);
    }
    if ($length > $maxBytes) {
        wb_json(array('status' => 'payload_too_large', 'information_only' => true), 413);
    }
    $raw = file_get_contents('php://input');
    $payload = json_decode((string)$raw, true);
    if (!is_array($payload)) {
        wb_json(array('status' => 'invalid_payload', 'error' => 'JSON object erwartet.', 'information_only' => true), 400);
    }
    return $payload;
}

function wb_next_sequence(string $dir, $lockHandle): int
{
    $sequencePath = $dir . '/sequence.txt';
    $current = 0;
    if (is_file($sequencePath)) {
        $current = (int)trim((string)file_get_contents($sequencePath));
    }
    $next = $current + 1;
    file_put_contents($sequencePath, (string)$next, LOCK_EX);
    return $next;
}

function wb_append_event(string $dir, string $kind, array $payload): array
{
    $lockPath = $dir . '/events.lock';
    $lock = fopen($lockPath, 'c');
    if (!$lock || !flock($lock, LOCK_EX)) {
        wb_json(array('status' => 'storage_error', 'error' => 'Lock konnte nicht erstellt werden.', 'information_only' => true), 500);
    }

    $sequence = wb_next_sequence($dir, $lock);
    $record = array(
        'sequence' => $sequence,
        'kind' => $kind,
        'received_at' => gmdate('c'),
        'payload' => $payload,
        'source' => 'kas_webhook_bridge',
        'information_only' => true,
    );

    $line = json_encode($record, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";
    file_put_contents($dir . '/events.ndjson', $line, FILE_APPEND | LOCK_EX);
    file_put_contents($dir . '/latest_' . $kind . '.json', json_encode($record, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
    flock($lock, LOCK_UN);
    fclose($lock);
    return $record;
}

function wb_latest_payload(string $dir, string $kind): array
{
    $path = $dir . '/latest_' . $kind . '.json';
    if (!is_file($path)) {
        return array(
            'bridge_type' => $kind === 'price' ? 'price' : 'order',
            'connection_state' => 'blocked',
            'item_count' => 0,
            'details' => array('KAS Bridge ist erreichbar, aber noch ohne ' . $kind . '-Event.'),
            'information_only' => true,
        );
    }
    $record = json_decode((string)file_get_contents($path), true);
    if (!is_array($record) || !isset($record['payload']) || !is_array($record['payload'])) {
        return array('connection_state' => 'error', 'item_count' => 0, 'information_only' => true);
    }
    $payload = $record['payload'];
    if ($kind === 'price') {
        $payload['bridge_type'] = $payload['bridge_type'] ?? 'price';
    } else {
        $payload = array(
            'bridge_type' => 'order',
            'event' => $payload,
            'timestamp' => $payload['timestamp'] ?? $record['received_at'],
            'source_name' => 'TradingView/Broker Orders',
            'information_only' => true,
        );
    }
    return $payload;
}

function wb_events_since(string $dir, int $since, int $limit): array
{
    $path = $dir . '/events.ndjson';
    if (!is_file($path)) {
        return array();
    }
    $events = array();
    $handle = fopen($path, 'r');
    if (!$handle) {
        return array();
    }
    while (($line = fgets($handle)) !== false) {
        $record = json_decode(trim($line), true);
        if (!is_array($record)) {
            continue;
        }
        $sequence = (int)($record['sequence'] ?? 0);
        if ($sequence > $since) {
            $events[] = $record;
        }
        if (count($events) >= $limit) {
            break;
        }
    }
    fclose($handle);
    return $events;
}

if (isset($_GET['health'])) {
    wb_json(array(
        'status' => 'ok',
        'service' => 'wertbegleiter_kas_webhook_bridge',
        'routes' => array('POST /tv/<token>/price', 'POST /tv/<token>/trade', 'GET /tv/<token>/events'),
        'information_only' => true,
    ));
}

$config = wb_load_config();
[$requestToken, $kind] = wb_path_route();
if (!hash_equals((string)$config['token'], $requestToken)) {
    wb_json(array('status' => 'forbidden', 'information_only' => true), 403);
}

if (!in_array($kind, array('price', 'trade', 'events'), true)) {
    wb_json(array('status' => 'not_found', 'information_only' => true), 404);
}

$dir = wb_storage_dir($config);
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET' && $kind === 'events') {
    $since = max(0, (int)($_GET['since'] ?? 0));
    $limit = min(500, max(1, (int)($_GET['limit'] ?? 100)));
    $events = wb_events_since($dir, $since, $limit);
    wb_json(array(
        'status' => 'ok',
        'events' => $events,
        'count' => count($events),
        'last_sequence' => count($events) ? (int)$events[count($events) - 1]['sequence'] : $since,
        'information_only' => true,
    ));
}

if ($method === 'GET' && ($kind === 'price' || $kind === 'trade')) {
    wb_json(wb_latest_payload($dir, $kind));
}

if ($method !== 'POST' || $kind === 'events') {
    wb_json(array('status' => 'method_not_allowed', 'information_only' => true), 405);
}

$payload = wb_read_json_body((int)$config['max_body_bytes']);
if ($kind === 'price') {
    $payload['bridge_type'] = $payload['bridge_type'] ?? 'price';
    $payload['source_name'] = $payload['source_name'] ?? 'TradingView/Broker Kurse';
} else {
    $payload['source'] = $payload['source'] ?? 'tradingview_webhook';
}

$record = wb_append_event($dir, $kind, $payload);
wb_json(array(
    'status' => 'stored',
    'kind' => $kind,
    'sequence' => $record['sequence'],
    'received_at' => $record['received_at'],
    'disclaimer' => 'Information only, keine Anlageberatung und keine Orderausfuehrung.',
    'information_only' => true,
));
