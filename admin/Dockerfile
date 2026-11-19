# ---- Build stage --------------------------------------------------------
# Build context is the repository root (docker-compose: context .., dockerfile admin/Dockerfile) so the
# page-editor canvas is built from the real public site components in frontend/src/site. vite.config.js
# fails the build if they are missing; the dev shim is never shipped (QA wave 2 D6).
# admin/Dockerfile.dockerignore keeps the context to admin/ and frontend/src/site.
FROM node:20-alpine AS build
WORKDIR /src/admin

# Install deps first for better layer caching.
COPY admin/package.json admin/package-lock.json* ./
RUN npm ci

COPY frontend/src/site /src/frontend/src/site
COPY admin/ ./

# VITE_API_BASE_URL is inlined at build time by Vite — pass it as a build
# arg so each deploy target (staging/prod) can point at its own API.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ARG VITE_PUBLIC_SITE_URL=http://localhost:3000
ENV VITE_PUBLIC_SITE_URL=$VITE_PUBLIC_SITE_URL

RUN npm run build

# ---- Serve stage ----------------------------------------------------------
FROM nginx:1.27-alpine AS serve

COPY --from=build /src/admin/dist /usr/share/nginx/html
COPY admin/nginx.conf /etc/nginx/conf.d/default.conf

RUN find /usr/share/nginx/html -type d -exec chmod 755 {} + && find /usr/share/nginx/html -type f -exec chmod 644 {} +

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
