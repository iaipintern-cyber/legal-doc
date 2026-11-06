# ============================================================
# Court of Inquiry -- FRONTEND image
#
# Build context is the PROJECT ROOT (setup.md section 2):
#   docker build --platform linux/amd64 -f frontend/Dockerfile --target production -t legal-frontend:1.0 .
#   docker build --platform linux/amd64 -f frontend/Dockerfile --target debug      -t legal-frontend-debug:1.0 .
#
# Stages:
#   build      -- npm ci + vite build (shared by production)
#   debug      -- Node + deps + source for Vite live reload (compose.debug.yml)
#   production -- nginx serving the compiled bundle (default target)
# ============================================================

# ============================================================
# Stage build -- build the React/Vite app
# ============================================================
FROM node:24-alpine AS build

WORKDIR /app

# Install deps first so this layer is cached across builds.
# The root .dockerignore keeps Windows node_modules out of the context.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build


# ============================================================
# Stage debug -- Node + dependencies + source (live reload)
# Used by compose.debug.yml; source is bind-mounted at runtime, so this
# stage mainly supplies the Linux node_modules (into the named volume).
# ============================================================
FROM node:24-alpine AS debug

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

EXPOSE 5173

# Vite must listen on 0.0.0.0 to be reachable through the published port.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


# ============================================================
# Stage production -- serve the static bundle with nginx (default)
# ============================================================
FROM nginx:1.27-alpine AS production

# Where /api/* is proxied to. compose.yml overrides this with the
# backend service name: -e BACKEND_URL=http://backend:8000
ENV BACKEND_URL=http://host.docker.internal:8000

# The official nginx image runs envsubst on *.template at startup,
# so ${BACKEND_URL} is filled in from the environment.
COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
