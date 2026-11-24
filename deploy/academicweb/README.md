# CRTDH on academicweb.iitkgp.ac.in

The website and its CMS on the CIC server itself, with no root, no Docker and no CIC changes. Apache keeps serving
the public site from the home folder. The CMS runs in the background as the `crtdh` user, and editors open it at
`https://crtdh.iitkgp.ac.in/cms/` (campus network only by default).

This server ignores `.htaccess`, and its home folder (virtiofs) fails when thousands of files are created, so:
- the programs (code, Python, Node, database, photos) live on the local disk in `/var/tmp/crtdh-crtdh`;
- Apache reaches the CMS through a small PHP bridge, `~/cms/index.php`;
- the settings and nightly backups live in `~/.crtdh` (mode 700, so Apache refuses it).

## Install (once, from the campus PC 10.111.26.20, logged in as crtdh)

```bash
curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/academicweb/install.sh -o /tmp/crtdh-install.sh && bash /tmp/crtdh-install.sh
```

It asks three things:
1. Turnstile keys for the contact form (press Enter to skip).
2. Your CMS admin login.
3. `yes`, to put the new site live.

Everything before that `yes` leaves the live site as it was.

## Bringing over everything from staging (content, photos, users)

1. On the homelab:
   `curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/staging/export-for-cic.sh | bash`
   This packs the staging CMS into one encrypted file at a random address on crtdh.annjan.in. It then prints the
   command to paste on the CIC server and a one-time pass phrase.
2. On the CIC server, paste the printed command and type the pass phrase when asked. The command either installs
   with the staging data (`CRTDH_IMPORT=…`) or, on an existing install, runs `~/.crtdh/crtdh import …`. Both:
   - save the current data first;
   - replace the content, photos and users in one step;
   - publish.

   Everyone signs in with their staging username and password.
3. Delete the file afterwards: the same homelab command with `| bash -s -- --cleanup`.

Not carried over: sign-in sessions, publish history and the agent's state (each server has its own),
contact-form messages, and the Claude connector's OAuth data.

## Day to day

| Command | Does |
|---|---|
| `~/.crtdh/crtdh status` | what is running, what is live, last backup |
| `~/.crtdh/crtdh update` | latest code from GitHub, restart (content kept) |
| `~/.crtdh/crtdh old-site` / `new-site` | switch back to the old hand-written site / to the newest CMS release |
| `~/.crtdh/crtdh access anywhere` / `campus` | who can open the CMS (the contact form always works) |
| `~/.crtdh/crtdh add-user` | another admin from the terminal (or use Users in the CMS) |
| `~/.crtdh/crtdh import <address>` | replace content, photos and users with a staging export, then publish |
| `~/.crtdh/crtdh logs web` (or `worker`, `agent`) | the last log lines |

Cron does three things:
- runs `crtdh watchdog` every 5 minutes and at reboot, so a stopped CMS starts again by itself;
- if the system has cleared `/var/tmp`, rebuilds the programs folder and restores the data from the last nightly backup (at most once an hour);
- at 03:23 each night, saves a database and photos backup to `~/.crtdh/backups` (the last 7 are kept).

## Where things are

| Path | What |
|---|---|
| `~/.crtdh/` (mode 700) | settings (`env`), nightly backups, old-site copy, this control script, logs of repairs |
| `/var/tmp/crtdh-crtdh/` (mode 700) | code, Python, Node, database, photos, releases, logs |
| `~/cms/index.php`, `~/cms/index.html`, `~/cms/.user.ini` | the PHP bridge to the CMS (campus check, forwarding) |
| `~/index.html`, `~/about/` … | the published site, copied in by the publish agent |

The old site's files stay where they were, and `crtdh old-site` serves them again. A full copy is in
`~/.crtdh/backups/old-site-*.tar.gz`. Old URLs such as `about.html` forward to the new pages; `mail.php` answers 410.

## How it was tested

The install was rehearsed end to end on a copy of this setup: Apache 2.4 with `AllowOverride None`, mod_php with
PATH_INFO, a symlinked home folder and a local `/var/tmp`. The rehearsal covered:
- install, sign in, edit, preview, publish, and the live check;
- backup with photos;
- old-site and new-site switching;
- outsiders refused (403) while the contact form stays open;
- hidden files (403), old URLs forwarding, and `mail.php` (410);
- the watchdog restart;
- wiping `/var/tmp`, then the automatic rebuild and restore from the nightly backup.
