#!/bin/sh
# Install the mounted keys with the ownership sshd's StrictModes wants, make sure the web volume belongs to the
# SFTP user, and seed a placeholder "existing site" the first time (the agent backs it up and keeps it as legacy-*).
set -eu
SEED=/seed
for f in ssh_host_ed25519_key authorized_key.pub; do
    [ -s "$SEED/$f" ] || { echo "sftp: $SEED/$f is missing; run deploy/staging/setup.sh" >&2; exit 1; }
done
install -d -m 0755 -o root -g root /etc/ssh/keys /etc/ssh/authorized_keys
install -m 0600 -o root -g root "$SEED/ssh_host_ed25519_key" /etc/ssh/keys/ssh_host_ed25519_key
install -m 0644 -o root -g root "$SEED/authorized_key.pub" /etc/ssh/authorized_keys/crtdh

WWW=/home/crtdh/www
chown crtdh:crtdh "$WWW"
chmod 0755 "$WWW"
if [ -z "$(ls -A "$WWW")" ]; then
    install -d -m 0755 -o crtdh -g crtdh "$WWW/public_html"
    cat > "$WWW/public_html/index.html" <<'HTML'
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<meta name="crtdh-staging-placeholder" content="1"><title>CRTDH staging</title></head>
<body><h1>CRTDH staging</h1><p>Nothing has been published yet. Publish once from the CMS.</p></body></html>
HTML
    chown crtdh:crtdh "$WWW/public_html/index.html"
    chmod 0644 "$WWW/public_html/index.html"
    echo "sftp: seeded placeholder site in $WWW/public_html"
fi
/usr/sbin/sshd -t
exec /usr/sbin/sshd -D -e
