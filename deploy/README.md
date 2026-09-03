# Deploying CRTDH CMS on a Ubuntu VPS

This directory is a self-contained Docker Compose stack: Postgres, the Django/DRF backend
(Gunicorn), the two static React apps (public site + admin SPA, each built and served by their
own nginx), a reverse-proxy nginx doing TLS termination and routing, and a certbot sidecar for
Let's Encrypt. Everything below assumes Docker Engine + the Compose plugin are already installed
on the server (`docker compose version` should work) and you have two DNS A records pointing at
the server's IP: your public domain (e.g. `crtdh.example.com`) and an admin subdomain (e.g.
`admin.crtdh.example.com`).

## 1. Get the code onto the server and configure it

```bash
git clone <your-repo-url> crtdh-cms   # or scp the crtdh-cms/ tree up
cd crtdh-cms/deploy
cp .env.example .env
```

Edit `.env`: set real domains, a strong `POSTGRES_PASSWORD`, a random `DJANGO_SECRET_KEY`
(e.g. `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`), and update the four
spelled-out `DJANGO_ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` / `DATABASE_URL` /
`PUBLIC_API_BASE_URL` / `ADMIN_API_BASE_URL` lines to match the domains you chose (see the
comments in `.env.example` — these don't auto-expand from the domain variables above them).

## 2. Bootstrap TLS certificates (first deploy only)

nginx refuses to start if the certificate files it's configured to use don't exist yet, and
certbot needs nginx running (to answer the HTTP validation request) before it can issue a real
certificate — so the standard chicken-and-egg fix is a throwaway self-signed cert first:

```bash
DOMAIN=$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)
mkdir -p certbot-bootstrap && cd certbot-bootstrap
mkdir -p "letsencrypt/live/$DOMAIN"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "letsencrypt/live/$DOMAIN/privkey.pem" \
  -out "letsencrypt/live/$DOMAIN/fullchain.pem" \
  -subj "/CN=$DOMAIN"
docker run --rm -v "$(pwd)/letsencrypt:/etc/letsencrypt" alpine chown -R 101:101 /etc/letsencrypt
cd ..
docker compose run --rm -v "$(pwd)/certbot-bootstrap/letsencrypt:/etc/letsencrypt" --entrypoint true nginx
docker run --rm -v crtdh-cms_certbot_conf:/dest -v "$(pwd)/certbot-bootstrap/letsencrypt:/src" alpine cp -r /src/. /dest/
rm -rf certbot-bootstrap
```

Now bring the stack up (nginx will start fine using the dummy cert):

```bash
docker compose up -d --build
```

Request the real certificate (covers both domains in one cert; certbot answers the challenge
through the `/.well-known/acme-challenge/` location the template already proxies to the shared
`certbot_www` volume):

```bash
PUBLIC_DOMAIN=$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)
ADMIN_DOMAIN=$(grep '^ADMIN_DOMAIN=' .env | cut -d= -f2)
EMAIL=$(grep '^CERTBOT_EMAIL=' .env | cut -d= -f2)
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d "$PUBLIC_DOMAIN" -d "$ADMIN_DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email
docker compose restart nginx
```

The `certbot` service's own container keeps running a renew-every-12h loop after this, so once
issued you don't need to think about renewal again.

## 3. First-run database setup

The `backend` container already runs `migrate` on every start (see its `command:` in
`docker-compose.yml`), so migrations are applied automatically. You still need a staff account
to log into the admin SPA, and — once, to populate real content — the seed command:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_from_mirror   # optional, see backend/README.md
```

## 4. Day-to-day operations

- **Deploy an update**: `git pull && docker compose up -d --build`
- **Logs**: `docker compose logs -f backend` (swap the service name as needed)
- **Change `PUBLIC_API_BASE_URL`/`ADMIN_API_BASE_URL`**: edit `.env`, then
  `docker compose build frontend admin && docker compose up -d frontend admin` — Vite bakes
  these in at build time, a plain restart won't pick up the change.
- **Backups**: back up the `pgdata` and `media_data` named volumes (e.g. via
  `docker run --rm -v crtdh-cms_pgdata:/data -v $(pwd):/backup alpine tar czf /backup/pgdata.tgz /data`,
  same idea for `media_data`); the two are the only state that isn't reproducible from the repo.
