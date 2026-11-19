#!/bin/bash
# Starts the single-container deployment: migrations, the optional demo seed,
# then uvicorn and nginx on $PORT.  The container stops as soon as either
# server exits, so the platform restarts it instead of serving a half-working
# app.
set -euo pipefail

# Bash runs as PID 1, which ignores SIGTERM unless a handler is installed, so
# the platform's stop signal is passed on and both servers shut down cleanly.
trap 'kill -TERM $(jobs -p) 2>/dev/null || true; wait || true; exit 0' TERM INT

export PORT="${PORT:-8080}"

envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf

cd /app
# The start-up steps run in the background and are waited for: bash runs the
# stop trap only between commands, so a stop signal would otherwise wait for
# a slow migration to finish.
alembic upgrade head &
wait $!

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  # The seeder fills only an empty table, so restarts never duplicate the
  # reviews.  A failing seed only warns: the API must still start.
  python scripts/seed_database.py &
  wait $! || echo "WARNING: the demo seed failed" >&2
fi

# nginx already logs every request, so uvicorn's own access log is off.
uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log &
uvicorn_pid=$!

# Wait for uvicorn to bind before starting nginx so the first request does
# not hit a 502 while the backend is still loading.  A uvicorn that dies
# while starting stops the container at once.
for _ in $(seq 1 50); do
  kill -0 "$uvicorn_pid" 2>/dev/null || exit 1
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null && break
  sleep 0.2
done

nginx -c /tmp/nginx.conf -g 'daemon off;' &

wait -n || true
exit 1
