# Cloudflare tunnel for CRTDH staging

The staging stack reaches the internet through one **remotely managed** Cloudflare tunnel. Its routes live in the
Cloudflare dashboard, and the `cloudflared` container only needs the tunnel **token**. Nothing on the homelab
opens a port.

| Hostname | What it is | Goes to |
|---|---|---|
| `crtdh.annjan.in` | public website (stands in for crtdh.iitkgp.ac.in) | `http://site:80` |
| `cms-crtdh.annjan.in` | admin app, CMS API, OAuth sign-in page | `http://gateway:80` |
| `contact-crtdh.annjan.in` | contact form relay: only `POST /api/v1/contact/` | `http://gateway:80` |
| `mcp-crtdh.annjan.in` | Claude connector: only `/mcp`, OAuth metadata, `/oauth/token/`, `/oauth/revoke_token/` | `http://mcp:8400` |

The service names (`site`, `gateway`, `mcp`) and ports come from `deploy/docker-compose.yml` and
`docker-compose.staging.yml`. `cloudflared` runs inside the same Docker network, so it reaches them by name.

The hostnames use a dash (`cms-crtdh`), not a dot (`cms.crtdh`). Cloudflare's free certificate covers one level
under `annjan.in` only.

**Why a separate contact hostname?** The gateway's nginx template (`deploy/nginx/templates/gateway.conf.template`)
has its own server block for `CONTACT_HOST`. That block allows only POST and OPTIONS, caps the body at 16 KB and
strips cookies. If `CONTACT_HOST` equalled `CMS_HOST`, nginx would warn "conflicting server name", ignore that
block, and staging would no longer test the production contact path. Also, if you put Cloudflare Access in front
of the CMS host (section 5), a shared host would put the public contact form behind Access too, and it would stop
working. So the kit adds `contact-crtdh.annjan.in`, the same layout as production's `contact.<domain>`.

---

## 1. Create the tunnel and copy its token (5 min)

1. Sign in at https://dash.cloudflare.com and open **Zero Trust** in the left menu. In the Zero Trust dashboard,
   go to **Networks → Tunnels**. Cloudflare moves menu items now and then: if you can't find it, search the
   dashboard for "Tunnels".
2. **Create a tunnel** → type **Cloudflared** → name `crtdh-staging` → **Save tunnel**.
3. On the "Install and run connectors" page, choose **Docker**. The page shows a command like
   `docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token eyJhIjoi...`.
   **Don't run it.** Copy only the long value after `--token` (it starts with `eyJ`).
   `setup.sh` asks for it and keeps it in `deploy/staging/secrets/tunnel.env` (0600, git-ignored).
4. Click **Next** to reach the routes page (section 2). The connector shows as "Inactive" until `setup.sh` starts
   `cloudflared`. That's expected.

The token works like a password: anyone who has it can run your tunnel. Keep it out of chat, email and shell
history. To replace it: in the dashboard, open the tunnel → **Refresh token** (or delete the tunnel and create a
new one), then run `deploy/staging/setup.sh --new-token`.

## 2. Public hostnames (routes) (10 min)

Open the tunnel → **Published application routes** (older dashboards call it **Public Hostname**) → **Add**. Add
these **six** routes. For each route: Subdomain, Domain `annjan.in`, Path, then Service Type and URL.

| # | Subdomain | Path | Service type | URL |
|---|---|---|---|---|
| 1 | `crtdh` | *(empty)* | HTTP | `site:80` |
| 2 | `cms-crtdh` | *(empty)* | HTTP | `gateway:80` |
| 3 | `contact-crtdh` | `^/api/v1/contact/$` | HTTP | `gateway:80` |
| 4 | `contact-crtdh` | *(empty)* | HTTP_STATUS | `404` |
| 5 | `mcp-crtdh` | `^/(mcp\|\.well-known/oauth-protected-resource(/mcp)?\|\.well-known/oauth-authorization-server\|oauth/token/\|oauth/revoke_token/)$` | HTTP | `mcp:8400` |
| 6 | `mcp-crtdh` | *(empty)* | HTTP_STATUS | `404` |

Route 5's path, ready to copy (it's one line, with no spaces):

```
^/(mcp|\.well-known/oauth-protected-resource(/mcp)?|\.well-known/oauth-authorization-server|oauth/token/|oauth/revoke_token/)$
```

This is the same rule as production's `deploy/cloudflared/config.yml.template`. `/oauth/authorize/` is
deliberately **not** on the MCP host: the sign-in page is served by the CMS host.

Rules:

- **Order matters.** Cloudflare checks routes from the top. For each host, the route **with** a path (3, 5) must
  sit **above** the catch-all **without** a path (4, 6). If the list shows them in another order, drag them into
  this order.
- Leave every **Additional application settings** option at its default. In particular, leave **HTTP Host
  Header** empty: the CMS and nginx rely on the original `Host` (`ALLOWED_HOSTS`, nginx `server_name`, the MCP
  server's Host check). Don't turn on "No TLS Verify" either: the services are plain HTTP inside the network, so
  it isn't needed.
- Saving a route creates a proxied (orange-cloud) CNAME `<name>.annjan.in → <tunnel id>.cfargotunnel.com` under
  DNS → Records. If a record with that name already exists, delete it first (DNS → Records), then add the route
  again.
- Routes 4 and 6 make the 404 explicit. If your dashboard has no HTTP_STATUS type, leave both out: a request that
  matches no route falls through to the tunnel's built-in last rule, which also answers 404 (`smoke.sh` checks
  this). **Never** add a catch-all for `mcp-crtdh` that points at `mcp:8400`: that would publish
  `/oauth/authorize/` on the MCP host.

Check after `setup.sh` has started the stack:

```bash
deploy/staging/dc.sh logs cloudflared | grep -i "registered tunnel connection"   # expect 4 lines
deploy/staging/smoke.sh                                                          # from any machine
```

## 3. Zone settings for annjan.in (check once)

These apply to the whole `annjan.in` zone, including the personal site, so change them only if they're not
already set:

- **SSL/TLS → Overview**: the mode doesn't affect tunnel routes (the tunnel is its own encrypted link). Leave it
  as it is for the rest of the zone.
- **SSL/TLS → Edge Certificates**: **Always Use HTTPS** on, **Minimum TLS Version** 1.2.
- **Security → Bots**: keep **Bot Fight Mode off** for staging. On the Free plan it can't be skipped per path. It
  may challenge the publish agent (which calls `cms-crtdh` from the homelab) and Claude's servers, and both fail
  on a challenge page. If it has to stay on, watch `deploy/staging/dc.sh logs publish-agent` for 403s.

## 4. MCP: restrict to Anthropic's IP ranges (optional for staging)

Production blocks everyone except Anthropic on the MCP host. Staging can do the same:

**Security → WAF → Custom rules → Create rule**

- Name: `MCP staging: Anthropic only`
- **Edit expression** and paste:
  ```
  (http.host eq "mcp-crtdh.annjan.in" and not ip.src in {160.79.104.0/21 153.61.208.0/20})
  ```
- Action: **Block** → Deploy.

These are Anthropic's published outbound IPv4 ranges (platform.claude.com/docs/en/api/ip-addresses, checked
19 Nov 2026; check again when you set this up).

- **Rule off**: anyone can reach the MCP host. Every call still needs an OAuth token, and the sign-in step needs
  a CMS password and TOTP. `smoke.sh` can test the MCP app from your laptop.
- **Rule on**: the claude.ai connector still works, because Claude connects from those ranges and nothing else
  needs the MCP host. Your browser only uses the CMS host for sign-in. From your laptop, `smoke.sh` then expects
  403 for the MCP host and skips the app checks.
- A claude.ai connector test needs the host open **to those ranges**. Rule off works too. A rule that blocks
  those ranges breaks it.

Optional: **Security → WAF → Rate limiting rules**, `http.host eq "contact-crtdh.annjan.in"`, about 3 requests per
10 seconds per IP → Block. The app limits each IP to 5 messages a minute on its own.

## 5. Cloudflare Access on the CMS host (off by default)

**Default for staging: no Access on `cms-crtdh`.** The CMS sign-in is password plus mandatory TOTP, with account
lockouts, so it's protected without Access. Staging holds the bundled public content and test accounts only.
Don't create real staff accounts on it.

**If you want Access anyway** (closer to production, where the CMS host is behind Access):

A. Protect the CMS for people:
1. Zero Trust → **Access → Applications → Add an application → Self-hosted**. Name `CRTDH staging CMS`, domain
   `cms-crtdh.annjan.in`, path empty.
2. Policy `Owner`: Action **Allow**, Include **Emails** = your address. Login method **One-time PIN**.

B. Let the publish agent through (otherwise it's sent to the Access sign-in page and can't publish):
1. **Access → Service auth → Service tokens → Create service token**, name `crtdh-staging-agent`. Copy the
   **Client ID** and **Client Secret** (shown once).
2. **Access → Applications → Add → Self-hosted**: name `CRTDH staging agent`, domain `cms-crtdh.annjan.in`, path
   `api/v1/agent/`. Policy: Action **Service Auth**, Include **Service Token** = `crtdh-staging-agent`. Nothing
   else. (The most specific path wins, so the rest of the host keeps policy A.)
3. On the homelab: `deploy/staging/setup.sh --with-access`. It asks for the Client ID and, with hidden input, the
   Client Secret. It writes `secrets/agent/access-secret.txt` (0600) and `access_client_id` in the agent's
   `config.ini`, and restarts the agent. The agent sends both as `CF-Access-Client-Id` / `CF-Access-Client-Secret`.
4. Check: `deploy/staging/dc.sh run --rm --no-deps publish-agent check` → `CMS connection : ok`.

The contact host and the MCP host stay outside Access in both cases. `smoke.sh` notices Access (a 302 to
`*.cloudflareaccess.com`) and adjusts the CMS checks.

To undo B, delete the two Access applications and the service token, delete `secrets/agent/access-secret.txt`,
then run `setup.sh` again.
