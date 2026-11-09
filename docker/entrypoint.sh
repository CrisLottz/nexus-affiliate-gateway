#!/bin/sh
# Container start-up: migrate, optionally seed the demo, then hand PID 1 to Gunicorn.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    flask --app nexus migrate
fi

if [ "${DEMO_MODE:-false}" = "true" ]; then
    flask --app nexus seed-demo
fi

# Cloud Run sends one request per concurrency slot; threads are cheap for I/O-bound work
# (database + CRM calls). Tune with GUNICORN_WORKERS / GUNICORN_THREADS.
exec gunicorn "nexus:create_app()" \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout 30 \
    --access-logfile - \
    --forwarded-allow-ips "*"
