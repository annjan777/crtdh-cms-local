#!/bin/sh
# One-time setup on Linux/macOS. Run from the folder that contains publish_agent/:  sh publish_agent/install/setup.sh
set -e
cd "$(dirname "$0")/../.."
PY=$(command -v python3 || command -v python)
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10 or newer is needed")'
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r publish_agent/requirements.txt
[ -f config.ini ] || cp publish_agent/config.example.ini config.ini
mkdir -p keys state
[ -f keys/crtdh_publish_ed25519 ] || .venv/bin/python -m publish_agent keygen keys/crtdh_publish_ed25519
chmod 700 keys; chmod 600 keys/crtdh_publish_ed25519
[ -f agent-secret.txt ] || { : > agent-secret.txt; }
chmod 600 agent-secret.txt
echo
echo "Done. Next (see publish_agent/README.md):"
echo "  1. Put this public key on the server:  $(cat keys/crtdh_publish_ed25519.pub)"
echo "  2. Paste the agent secret into agent-secret.txt (one line)."
echo "  3. Edit config.ini (user, cms url), then:  .venv/bin/python -m publish_agent check --trust-host-key"
