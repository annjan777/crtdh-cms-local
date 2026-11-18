#!/bin/sh
# CRTDH server discovery (WS0.7). Read-only: it only prints facts about the hosting account.
# Run from the whitelisted PC:   ssh USER@academicweb.iitkgp.ac.in 'WEB_ROOT=~/public_html sh -s' < discover.sh
# (`python -m publish_agent check` runs it for you when the account allows shell commands.)
WEB_ROOT="${WEB_ROOT:-$HOME/public_html}"
say() { printf '%s: %s\n' "$1" "$2"; }
have() { command -v "$1" >/dev/null 2>&1; }

say user "$(id -un 2>/dev/null || whoami)"
say home "$HOME"
say os "$(uname -sr 2>/dev/null)"
say web_root "$WEB_ROOT"
if [ -L "$WEB_ROOT" ]; then say web_root_kind "symlink -> $(readlink "$WEB_ROOT")"
elif [ -d "$WEB_ROOT" ]; then say web_root_kind "directory"
else say web_root_kind "missing"; fi
say web_root_owner "$(ls -ld "$WEB_ROOT" 2>/dev/null)"
say web_root_parent "$(ls -ld "$(dirname "$WEB_ROOT")" 2>/dev/null)"
say web_root_files "$(find "$WEB_ROOT" -type f 2>/dev/null | wc -l | tr -d ' ')"
say web_root_size_kb "$(du -sk "$WEB_ROOT" 2>/dev/null | cut -f1)"
say htaccess_present "$( [ -f "$WEB_ROOT/.htaccess" ] && echo yes || echo no)"
say same_fs_as_home "$( [ "$(df -P "$HOME" 2>/dev/null | awk 'NR==2{print $1}')" = "$(df -P "$WEB_ROOT" 2>/dev/null | awk 'NR==2{print $1}')" ] && echo yes || echo no)"
say df "$(df -Pk "$WEB_ROOT" 2>/dev/null | awk 'NR==2{print $2" total KB, "$4" free KB"}')"
say free_kb "$(df -Pk "$WEB_ROOT" 2>/dev/null | awk 'NR==2{print $4}')"
if have quota; then say quota "$(quota -s 2>/dev/null | tail -n +3 | tr -s ' ' | head -3 | tr '\n' ';')"; else say quota "quota command not available"; fi
for t in php python3 python perl; do
  if have "$t"; then say "$t" "$("$t" --version 2>&1 | grep -m1 .)"; else say "$t" "not installed"; fi
done
say passwd "$(have passwd && echo available || echo 'not available')"
say ssh_dir "$(ls -ld "$HOME/.ssh" 2>/dev/null || echo missing)"
say authorized_keys "$(ls -l "$HOME/.ssh/authorized_keys" 2>/dev/null || echo missing)"
say web_server_hint "$(ls -d /etc/httpd /etc/apache2 /etc/nginx 2>/dev/null | tr '\n' ' ')"
