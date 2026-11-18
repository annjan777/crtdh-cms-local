# CRTDH publish agent

A small program that runs on the **one campus PC allowed to reach the web server** (10.111.26.20).
It asks the private CMS every 30 seconds whether there is a new website build. If there is, it downloads it,
checks it is genuine, uploads it to `academicweb.iitkgp.ac.in` over SFTP, switches the live site to it, checks
that https://crtdh.iitkgp.ac.in/ shows it, and tells the CMS "live" (or "failed", with the reason).

If an upload breaks part way through, the live site doesn't change. The last few releases stay on the server, so one command puts the previous one back.

You need: Python 3.10 or newer, the hosting account user name and password (only used once, to add the key), and the
**agent secret** from whoever runs the CMS. About 15 minutes.

---

## 1. Install (once)

1. Install Python 3.10+ from https://www.python.org/downloads/ (Windows: tick **"Add python.exe to PATH"**).
2. Copy the `publish_agent` folder from the repository into a folder on the PC:
   - Windows: `C:\crtdh-agent\publish_agent`
   - Linux: `/opt/crtdh-agent/publish_agent` · macOS: `~/crtdh-agent/publish_agent`
3. Run the setup script from that folder (`C:\crtdh-agent`, etc.):
   - Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File publish_agent\install\setup.ps1`
   - Linux / macOS: `sh publish_agent/install/setup.sh`

   This creates `.venv` (Python packages: only `paramiko`), `config.ini`, an SSH key in `keys/`, and an empty
   `agent-secret.txt`. It prints the **public key** line (starts with `ssh-ed25519`).

> The commands below use `python` to mean the agent's own Python:
> Windows `.\.venv\Scripts\python.exe`, Linux/macOS `.venv/bin/python`. Run them from the agent folder.

## 2. Put the key on the server (once)

Log in with the password from this PC (`ssh USER@academicweb.iitkgp.ac.in`, or WinSCP/FileZilla if SSH commands
are blocked) and add the public key line to `~/.ssh/authorized_keys`:

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'ssh-ed25519 AAAA...your line... crtdh-publish-agent' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

With WinSCP/FileZilla: create the `.ssh` folder, upload a file named `authorized_keys` that contains the line, and set the folder to 700 and the file to 600.
If the server does not allow keys, see "Password instead of a key" below.

After the key works, change the account password (`passwd` over SSH) so that the password sent by email no longer works.
Don't write the password down anywhere on this PC.

## 3. Configure (once)

1. Paste the agent secret (one line) into `agent-secret.txt`. Don't put it in `config.ini`.
2. Edit `config.ini`: set `[sftp] user`, `[cms] url`. Leave the rest at the defaults for now.
3. Run the check. The first time, add `--trust-host-key`:

   ```
   python -m publish_agent check --trust-host-key
   ```

   It prints the server's fingerprint (save it in the runbook), then a report like:

   ```
   Web root               : /home/crtdh/public_html (exists: yes ...)
   Symlinks allowed       : yes
   .htaccess honoured     : yes
   Free space (KB)        : 512000
   RECOMMENDED STRATEGY   : symlink - ...
   CMS connection         : ok (agent secret accepted)
   ```

   If "Web root" is wrong, set `web_root` to one of the listed "Other web-root folders" and run `check` again.
   Copy the whole report into the project runbook (this is the WS0.7 server discovery).
   If the account allows SSH commands, the report also includes the output of `discover.sh` (PHP/Python, quota). To run that script by hand:
   `ssh USER@academicweb.iitkgp.ac.in 'sh -s' < publish_agent/discover.sh`.

4. Optional backup of the current live site (the agent also does this before its first publish):
   `python -m publish_agent backup` → `state/backups/live-site-before-agent-*.tar.gz`. Keep this file.

5. Try one publish without changing anything: `python -m publish_agent --dry-run run --once`.

## 4. Run it all the time

Pick the file for the PC's operating system in `publish_agent/install/`:

| OS | File | How |
|---|---|---|
| Windows | `windows-task.xml` | Task Scheduler → *Import Task…* → choose the file → **Change User or Group** to your account → OK (enter your *Windows* password when asked). Right-click → *Run*. |
| Linux | `crtdh-publish-agent.service` | set `User=`; `sudo cp` to `/etc/systemd/system/`; `sudo systemctl enable --now crtdh-publish-agent` |
| macOS | `in.ac.iitkgp.crtdh.publish-agent.plist` | replace `CHANGE_ME`; copy to `~/Library/LaunchAgents/`; `launchctl load -w …` |

The agent starts at boot/logon and restarts itself if it stops. It refuses to run twice at the same time.
The PC must be on and on the campus network for publishing to work. While it is off, the CMS shows
"Waiting for upload machine (last seen …)".

## 5. Everyday commands

| What | Command |
|---|---|
| What is live, what is kept, last result | `python -m publish_agent status` |
| Put the previous release back | `python -m publish_agent rollback` |
| Put a specific release back | `python -m publish_agent rollback --to 2026-11-19T09-30-00Z-3f2a1c` |
| Back to the site from before the agent | `rollback --to legacy-…` (the id is shown in `status`) |
| One publish pass now | `python -m publish_agent run --once` |
| See everything it would do, change nothing | add `--dry-run` before the command |
| More detail on screen | add `--verbose` |
| Logs | `state/logs/agent.log` (rotated, 5 × 1 MB; never contains passwords or the secret) |

## How a publish works

1. `GET /api/v1/agent/next/` (signed with the agent secret: HMAC-SHA256 over method, path, timestamp and body hash).
2. Download the tarball. Check its SHA-256 and the CMS's signature. Unpack it safely (only files and folders, no `..`).
3. Upload `site/` into `releases/<snapshot>.partial/`. Each file goes up under a temporary name and is then renamed, so a file is never left half written.
   If the connection drops, the agent reconnects and continues where it stopped (up to 3 tries). Files already there are skipped.
4. Upload the tarball's new `media/` files into the shared `_media/` folder (served at `/_media/`; `/media/` is the Media & Gallery page). Files are named by content hash, so an image already on the server is never uploaded again.
5. Rename `<snapshot>.partial` → `<snapshot>`, then **switch** (see below) and save `state.json` on the server.
6. Load `verify_url` and look for `<meta name="crtdh-build" content="<snapshot>">`. If it's not there after 5 tries, the agent switches back to the previous release and reports "failed".
7. Report "live". Delete releases older than `keep_releases`, any leftover `.partial` folders, and media files that no kept release uses.
   The site that was there before the agent (`legacy-…`) is never deleted automatically.

If the disk quota is full, the upload is marked failed with a message that mentions the quota. The half-finished upload is removed to free space, and the live site stays as it was.

## Switch strategies

`check` recommends one, and `strategy = auto` uses that recommendation. Once the server has been set up with a strategy, the agent keeps using it.

| Strategy | Server layout | Switch | Downtime |
|---|---|---|---|
| `symlink` (preferred) | `public_html` → link to `crtdh-releases/releases/<id>`; media in `crtdh-releases/_media` | one atomic rename of a new link | none |
| `htaccess` | releases in `public_html/_crtdh/releases/<id>`; `.htaccess` rewrites every request to the live one | one atomic rename of `.htaccess` | none |
| `swap` | `public_html` *is* the live release; old ones in `crtdh-releases/releases/` | three folder renames | under a second, while the folders are renamed |
| `copy` (last resort) | files overwritten in `public_html` one by one | per-file renames | visitors may briefly see a mix of old and new pages |

The first publish backs up the existing site to this PC. With `symlink` and `swap`, it then moves the old site to `releases/legacy-<time>` (if `public_html` is already a link, the folder it points to is left in place and only recorded); with `htaccess`, the agent only ever writes its own `# BEGIN/# END crtdh-publish-agent` block, and any other rules in `.htaccess` are kept. Rolling back to `legacy-…` brings the old site back.

**Changing strategy**: don't flip the setting on a live site. Roll back to `legacy-…`, move the agent's folders
(`crtdh-releases/` or `public_html/_crtdh/`) aside, set the new `strategy`, then publish again.

Things to confirm once on the real host, because the tests only simulate them: the web server follows the `public_html` link (`check` tests this over HTTP when `verify_url` is set), and `.htaccess` rewrite rules are allowed.

## Password instead of a key

Only if the server refuses keys: leave `key_file` empty and store the password in the system keyring:
`pip install keyring` (inside `.venv`), then `python -m publish_agent set-password`. The password is kept by
Windows Credential Manager / macOS Keychain / Secret Service, never in a file the agent writes.
For a one-off check you can also type it: `python -m publish_agent check --password`.

## Troubleshooting

| Message | What to do |
|---|---|
| `server host key not trusted yet` | Run `check --trust-host-key` once and compare the fingerprint with the runbook. |
| `host key CHANGED` | **Stop.** Ask whoever manages the server whether it was reinstalled. Don't trust the new key until they confirm. |
| `CMS refused the agent (401)` | Wrong secret in `agent-secret.txt`, or the PC clock is off by more than 5 minutes. |
| `cannot reach the CMS` | PC offline, or the CMS is down. The agent keeps retrying (up to every 10 min). |
| `disk quota is probably full` | `check` shows free space. Lower `keep_releases`, or delete old `crtdh-releases/releases/legacy-*` (after confirming you have its backup). |
| `the site did not show the new build` | Already rolled back. Check that the build includes the `crtdh-build` meta tag and that no cache is serving old pages. |
| `another copy … is already running` | Normal if the scheduled task is running. Stop it before running `run` by hand. |

## Runbook: manual upload when the CMS (or this agent) is down

Use this only in an emergency. The next agent publish replaces whatever you upload here.

1. Get a build: from a developer machine, build the site (`frontend/build/client/`), or use a tarball the CMS
   produced earlier (`state/work/*.tar.gz` on this PC, or any `crtdh-site-<id>.tar.gz`).
2. Connect from this PC with WinSCP/FileZilla (SFTP, host `academicweb.iitkgp.ac.in`, port 22, private key
   `keys/crtdh_publish_ed25519`; in WinSCP convert it to .ppk when asked).
3. Upload the `site/` contents into a **new** folder `crtdh-releases/releases/manual-<date>/`. With `htaccess`, use `public_html/_crtdh/releases/manual-<date>/` instead.
   Upload any new files from the tarball's `media/` into the shared `_media/` folder from the table above.
   With `symlink`, also create a link `_media` → `../../_media` inside the new folder. WinSCP can do this from the context menu: *New → Link*.
4. Switch:
   - `symlink`: create a link `public_html.new` → `crtdh-releases/releases/manual-<date>`, then rename it over `public_html`. If renaming over isn't allowed, delete the old `public_html` link first; the site is down for a moment.
   - `htaccess`: edit `public_html/.htaccess` and replace the release id in the three places it appears.
   - `swap` / `copy`: rename `public_html` → `crtdh-releases/releases/<current id>` and the new folder → `public_html`, then move `_media` from the old folder into the new one.
5. Open https://crtdh.iitkgp.ac.in/ and check the page.
6. When the agent is back, run `python -m publish_agent status`. It detects the link or `.htaccess` you changed, but it does
   not know a `manual-…` release by name, so publish once from the CMS to return to normal.

If everything is broken, restore `state/backups/live-site-before-agent-*.tar.gz`: unpack it and upload its `site/` folder into `public_html` (after moving the agent's link aside).

## For developers

- Code: `agent.py` (CLI), `deploy.py` (flow, retention, media GC), `strategies.py`, `layout.py`, `remote.py`
  (SFTP helpers), `cmsclient.py` (HMAC), `bundle.py` (safe unpack), `discover.py` + `discover.sh`, `logutil.py` (redaction).
- Tests: `pip install -r publish_agent/requirements-dev.txt; python -m pytest publish_agent/tests -p no:asyncio`.
  They run an in-process paramiko SFTP server (with fault injection for dropped connections and a full quota), a fake CMS, and a fake web server.
- Manual sandbox: `python -m publish_agent.tests.run_fakes /tmp/crtdh-e2e` (fake CMS on :8500, SFTP on :2222), then
  `CRTDH_AGENT_SECRET=local-test-agent-secret-0123456789 python -m publish_agent -c /tmp/crtdh-e2e/config.ini run --once`.
- Wire format (agreed with backend-core): `X-Agent-Timestamp` + `X-Agent-Signature` =
  hex HMAC-SHA256(secret, `METHOD\nPATH\nTS\nsha256hex(body)`); build signature =
  HMAC-SHA256(secret, `crtdh-build-v1\n<publish_id>\n<snapshot_id>\n<sha256>`); statuses `uploading|live|failed`,
  steps `download|verify|upload|switch|check_live`. The CMS rejects a replayed (timestamp, signature) pair, so the client never sends the same request twice within one second.
