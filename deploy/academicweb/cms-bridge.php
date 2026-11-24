<?php
// CRTDH CMS on academicweb: https://crtdh.iitkgp.ac.in/cms/index.php/<path> -> the CMS on 127.0.0.1.
//
// This server ignores .htaccess, so Apache cannot route or proxy for us; PHP can. Installed as ~/cms/index.php by
// deploy/academicweb/setup.sh. It forwards only to the CMS, sets the forwarding headers itself (never trusting the
// client's), lets only campus addresses in (the public contact form excepted), and holds no secrets.
//   /cms/index.php/api/...   -> CMS /api/...   (the API, photos, the contact form)
//   /cms/index.php/oauth/... -> CMS /oauth/... (the Claude connector's sign-in and consent page)
//   /cms/index.php/<other>   -> CMS /cms/<other> (the editor screens)
// The same file, installed as ~/mcp/index.php with $MODE = 'mcp', is the Claude connector's address:
//   /mcp/index.php/mcp, /mcp/index.php/.well-known/oauth-*, /mcp/index.php/oauth/token|revoke_token
//   -> the MCP server; reachable from campus and from Anthropic's published outbound range only.
$CMS_PORT = 8650;        // written by setup.sh
$ACCESS = 'campus';      // campus | anywhere   (~/.crtdh/crtdh access ...)
$MODE = 'cms';           // cms | mcp           (written by setup.sh)

// The raw (still percent-encoded) path after /cms/index.php, so photo names with spaces pass through unchanged.
$uri = $_SERVER['REQUEST_URI'] ?? '/';
$query = '';
if (($q = strpos($uri, '?')) !== false) {
    $query = substr($uri, $q + 1);
    $uri = substr($uri, 0, $q);
}
$self = $_SERVER['SCRIPT_NAME'] ?? '/cms/index.php';
$info = (strpos($uri, $self) === 0) ? substr($uri, strlen($self)) : '';
if ($info === '') {
    if ($MODE === 'mcp') {
        http_response_code(404);
        exit;
    }
    header('Location: /cms/index.php/', true, 302);
    exit;
}
if (strpos(rawurldecode($info), '..') !== false || !preg_match('#^/[A-Za-z0-9._~!$&\'()*+,;=:@%/-]*$#', $info)) {
    http_response_code(400);
    exit;
}
if ($MODE === 'mcp') {
    // Only what Claude needs: the MCP endpoint, the OAuth metadata, token and revocation.
    if (!preg_match('#^/(mcp|\.well-known/oauth-(authorization-server|protected-resource(/mcp)?)|oauth/(token|revoke_token)/)$#', $info)) {
        http_response_code(404);
        exit;
    }
    $target = $info;
} else {
    $target = (strpos($info, '/api/') === 0 || strpos($info, '/oauth/') === 0) ? $info : '/cms' . $info;
}
$isContact = $MODE === 'cms' && (bool) preg_match('#^/api/v1/contact/?$#', $target);

$ip = $_SERVER['REMOTE_ADDR'] ?? '';
$campus = (bool) preg_match('/^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|127\.0\.0\.1$|::1$)/', $ip);
// Anthropic's published outbound range for connector calls (platform.claude.com/docs/en/api/ip-addresses).
$v4 = ip2long($ip);
$anthropic = $v4 !== false && (($v4 & 0xFFFFF800) === (ip2long('160.79.104.0') & 0xFFFFF800));
$allowed = $ACCESS === 'anywhere' || $campus || $isContact || ($MODE === 'mcp' && $anthropic);
if (!$allowed) {
    http_response_code(403);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    echo '<!doctype html><meta charset="utf-8"><title>CRTDH CMS</title>'
        . '<p style="font:16px/1.5 system-ui,sans-serif;max-width:36em;margin:4em auto">'
        . ($MODE === 'mcp' ? 'This address is for the CRTDH Claude connector only.'
                           : 'The CRTDH website editor opens only from the IIT Kharagpur campus network.') . '</p>';
    exit;
}

@ini_set('zlib.output_compression', '0');
@set_time_limit(330);
while (ob_get_level() > 0) {
    ob_end_clean();
}

$drop = ['host', 'connection', 'content-length', 'transfer-encoding', 'expect', 'forwarded', 'x-forwarded-for',
         'x-forwarded-host', 'x-forwarded-proto', 'x-real-ip', 'cf-connecting-ip', 'proxy', 'te', 'upgrade'];
$headers = [];
$contentType = '';
foreach (getallheaders() as $name => $value) {
    $lower = strtolower($name);
    if (in_array($lower, $drop, true)) {
        continue;
    }
    if ($lower === 'content-type') {
        $contentType = $value;
    }
    $headers[$lower] = "$name: $value";
}
$https = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
$headers['x-forwarded-for'] = 'X-Forwarded-For: ' . $ip;
$headers['x-forwarded-host'] = 'X-Forwarded-Host: ' . preg_replace('/[^A-Za-z0-9.:-]/', '', $_SERVER['HTTP_HOST'] ?? '');
$headers['x-forwarded-proto'] = 'X-Forwarded-Proto: ' . ($https ? 'https' : 'http');
$headers['expect'] = 'Expect:';
if ($MODE === 'mcp') {
    // The MCP server checks Host against its public address (DNS-rebinding protection).
    $headers['host'] = 'Host: ' . preg_replace('/[^A-Za-z0-9.:-]/', '', $_SERVER['HTTP_HOST'] ?? '');
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$ch = curl_init('http://127.0.0.1:' . $CMS_PORT . $target . ($query !== '' ? '?' . $query : ''));
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
if (!in_array($method, ['GET', 'HEAD', 'OPTIONS'], true)) {
    if (stripos($contentType, 'multipart/form-data') === 0 && (count($_FILES) || count($_POST))) {
        // PHP already parsed the upload: send it on as a new multipart body (curl writes its own boundary).
        $fields = [];
        foreach ($_POST as $k => $v) {
            if (is_string($v)) {
                $fields[$k] = $v;
            }
        }
        foreach ($_FILES as $k => $f) {
            if (is_array($f['tmp_name'])) {
                continue;  // the CMS never sends file arrays
            }
            if ($f['error'] !== UPLOAD_ERR_OK) {
                http_response_code(413);
                header('Content-Type: application/json');
                echo json_encode(['error' => ['code' => 'UPLOAD_TOO_LARGE',
                    'message' => 'This file is larger than the server accepts. Try a smaller photo.']]);
                exit;
            }
            $fields[$k] = new CURLFile($f['tmp_name'], $f['type'] ?: 'application/octet-stream', $f['name']);
        }
        unset($headers['content-type']);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $fields);
    } else {
        curl_setopt($ch, CURLOPT_POSTFIELDS, file_get_contents('php://input'));
    }
}
if ($method === 'HEAD') {
    curl_setopt($ch, CURLOPT_NOBODY, true);
}
curl_setopt($ch, CURLOPT_HTTPHEADER, array_values($headers));
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
curl_setopt($ch, CURLOPT_TIMEOUT, 320);
curl_setopt($ch, CURLOPT_ENCODING, null);
$skip = ['transfer-encoding', 'connection', 'keep-alive', 'content-length'];
curl_setopt($ch, CURLOPT_HEADERFUNCTION, function ($ch, $line) use ($skip, $MODE) {
    $trimmed = rtrim($line, "\r\n");
    if (preg_match('#^HTTP/\S+\s+(\d{3})#', $trimmed, $m)) {
        http_response_code((int) $m[1]);
    } elseif ($trimmed !== '' && strpos($trimmed, ':') !== false) {
        $name = strtolower(trim(substr($trimmed, 0, strpos($trimmed, ':'))));
        if (in_array($name, $skip, true)) {
            return strlen($line);
        }
        if ($name === 'location') {
            // The CMS's own paths, back into this bridge's address space.
            $value = trim(substr($trimmed, strpos($trimmed, ':') + 1));
            if ($MODE === 'cms') {
                // Sign-in for the Claude connector: /cms/login?next=/oauth/authorize/... must come back here.
                $value = str_replace(['next=%2Foauth%2F', 'next=/oauth/'],
                                     ['next=%2Fcms%2Findex.php%2Foauth%2F', 'next=/cms/index.php/oauth/'], $value);
                $value = preg_replace('#^/(cms|api|oauth)/#', '/cms/index.php/$1/', $value);
                $value = preg_replace('#^/cms/index\.php/cms/#', '/cms/index.php/', $value);
            }
            $trimmed = 'Location: ' . $value;
        }
        header($trimmed, false);
    }
    return strlen($line);
});
curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($ch, $chunk) {
    echo $chunk;
    flush();
    return strlen($chunk);
});
if (curl_exec($ch) === false && !headers_sent()) {
    http_response_code(502);
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    echo json_encode(['error' => ['code' => 'CMS_UNAVAILABLE',
        'message' => 'The website editor is not running right now. It restarts by itself within 5 minutes.']]);
}
curl_close($ch);
