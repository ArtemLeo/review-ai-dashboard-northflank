# Single-container image: nginx serves the built dashboard on $PORT and
# proxies the API to uvicorn inside the container.

FROM node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# PGCONNECT_TIMEOUT makes the database driver give up on a server that does
# not answer, so a hung database fails the start-up instead of blocking it.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    PGCONNECT_TIMEOUT=10

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx-light gettext-base \
    && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled /etc/nginx/conf.d

WORKDIR /app

COPY backend/requirements.txt ./
# Patch the packaging tools inherited from the base image before installing
# application dependencies; pin the versions to the reviewed releases.
RUN python -m pip install --no-cache-dir --upgrade pip==26.2 setuptools==84.1.0 \
    && python -m pip install --no-cache-dir -r requirements.txt

# The code stays owned by root: the unprivileged runtime user can read it but
# never modify it.  Everything the servers write goes to /tmp.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY deploy/nginx.conf.template /etc/nginx/nginx.conf.template
COPY frontend/nginx-headers.conf frontend/nginx-base-headers.conf /etc/nginx/
COPY --from=frontend /build/dist /usr/share/nginx/html
COPY backend/ ./
COPY deploy/start.sh /usr/local/bin/start.sh

USER appuser

EXPOSE 8080

# The worker service runs this image with a celery command and serves no
# HTTP, so the probe skips it; the app container is probed on its own $PORT.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD grep -qa celery /proc/1/cmdline || python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health', timeout=3)" || exit 1

# The worker service reuses this image with its own command (see AGENTS.md).
CMD ["bash", "/usr/local/bin/start.sh"]
