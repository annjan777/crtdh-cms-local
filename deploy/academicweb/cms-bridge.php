<?php
// CRTDH CMS bridge for academicweb: used only when Apache cannot proxy (no mod_proxy for .htaccess).
// The .htaccess host block (crtdh access) sends /cms/ and /api/ here; this passes the request to the CMS on
// 127.0.0.1 and streams the answer back. It forwards nothing else, sets the forwarding headers itself (never
// trusting the client's), and has no settings of its own. Installed by deploy/academicweb/setup.sh as
// ~/_crtdh_cms.php; the port comes from the line below, which setup writes.
$CMS_PORT = 8650;

$uri = $_SERVER['REQUEST_URI'] ?? '/';
if (!preg_match('#^/(cms|api)(/|$|\?)#', $uri)) {
    http_response_code(404);
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
$headers['x-forwarded-for'] = 'X-Forwarded-For: ' . ($_SERVER['REMOTE_ADDR'] ?? '');
$headers['x-forwarded-host'] = 'X-Forwarded-Host: ' . preg_replace('/[^A-Za-z0-9.:-]/', '', $_SERVER['HTTP_HOST'] ?? '');
$headers['x-forwarded-proto'] = 'X-Forwarded-Proto: ' . ($https ? 'https' : 'http');
$headers['expect'] = 'Expect:';

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$ch = curl_init('http://127.0.0.1:' . $CMS_PORT . $uri);
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
                    'message' => 'The file is larger than this server accepts through the PHP bridge.']]);
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
curl_setopt($ch, CURLOPT_ENCODING, null);  // pass bytes through as the CMS sent them
$skip = ['transfer-encoding', 'connection', 'keep-alive', 'content-length'];
curl_setopt($ch, CURLOPT_HEADERFUNCTION, function ($ch, $line) use ($skip) {
    $trimmed = rtrim($line, "\r\n");
    if (preg_match('#^HTTP/\S+\s+(\d{3})#', $trimmed, $m)) {
        http_response_code((int) $m[1]);
    } elseif ($trimmed !== '' && strpos($trimmed, ':') !== false) {
        $name = strtolower(trim(substr($trimmed, 0, strpos($trimmed, ':'))));
        if (!in_array($name, $skip, true)) {
            header($trimmed, false);
        }
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
        'message' => 'The CMS is not running right now. On the server run: ~/.crtdh/crtdh start']]);
}
curl_close($ch);
