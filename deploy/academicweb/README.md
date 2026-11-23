# CRTDH on academicweb.iitkgp.ac.in

The website and its CMS on the CIC server itself: no root, no Docker. Apache keeps serving the public site from
the home folder; the CMS runs in the background as the `crtdh` user and editors open it at
`https://crtdh.iitkgp.ac.in/cms/` (campus network only by default).

## Install (once, from the campus PC 10.111.26.20, logged in as crtdh)

```bash
ulimit -n 65536; mkdir -m 700 ~/.crtdh && git clone -b dev https://github.com/annjan777/crtdh-cms-local.git ~/.crtdh/app && bash ~/.crtdh/app/deploy/academicweb/setup.sh
```

It asks three things: Turnstile keys for the contact form (Enter to skip), your CMS admin login, and `yes` to put
the new site live. Everything before that `yes` leaves the live site as it was.

## Day to day

| Command | Does |
|---|---|
| `~/.crtdh/crtdh status` | what is running, what is live |
| `~/.crtdh/crtdh update` | latest code from GitHub, restart (content kept) |
| `~/.crtdh/crtdh old-site` / `new-site` | switch back to the old hand-written site / to the newest CMS release |
| `~/.crtdh/crtdh access anywhere` / `campus` | who can open the CMS login page |
| `~/.crtdh/crtdh add-user` | another admin from the terminal (or use Users in the CMS) |
| `~/.crtdh/crtdh logs web` (or `worker`, `agent`) | the last log lines |

Cron runs `crtdh watchdog` every 5 minutes and at reboot, so a stopped CMS starts again by itself.

## Where things are

| Path | What |
|---|---|
| `~/.crtdh/` (mode 700, refused by `.htaccess`) | code, Python, Node, settings (`env`), database, photos, logs, old-site copy |
| `~/.htaccess` | `crtdh-host` block (hidden files, campus-only CMS, route to the CMS), then the publish agent's block |
| `~/_crtdh/` | published releases and photos (served through the agent's rewrite rules only) |
| `~/_crtdh_cms.php`, `~/.user.ini` | only when Apache can't proxy: the PHP bridge to the CMS |

The old site's files stay where they were; `crtdh old-site` serves them again. A full copy is in
`~/.crtdh/backups/old-site-*.tar.gz`.

## How it was tested

`setup.sh` was rehearsed end to end on Apache 2.4 with `AllowOverride FileInfo` and a symlinked home folder, once
with mod_proxy and once without it (PHP bridge): install, sign in, edit, publish, live check, old-site/new-site,
watchdog restart, campus-only refusal, hidden files (403), old URLs (301), `mail.php` (410).
