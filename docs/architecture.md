# Architecture and code walkthrough

A guided reading order through the code: each step says what to open, what it does and why it was built that way. Reading it top to bottom takes about an hour.

## Map

```
nexus/
  __init__.py        create_app(): the only place where everything is wired together
  config.py          Settings (pydantic-settings): env vars, validated at start-up
  db.py              engine + per-request session in flask.g
  models.py          User, Promoter, Lead, OutboxEvent
  security.py        password hashing, current_user, login_required
  validation.py      parse_body(): Pydantic → 422 with field errors
  extensions.py      CSRFProtect, Limiter
  outbox.py          enqueue / process / flush / requeue + backoff
  crm/               CRMProvider protocol, MockProvider, HubSpotProvider
  blueprints/        one file per area of the API (auth, users, promoters, leads,
                     dashboard, public, internal, spa, health)
  demo.py, cli.py, migrate.py
migrations/          Alembic (env.py reads the URL from the app settings)
frontend/            Vite + React + TS + Tailwind; builds into nexus/static/app
tests/               pytest; every test runs on a database built by the real migrations
```

## 1. Start-up — `nexus/__init__.py`, `nexus/config.py`

`create_app()` is an application factory: tests build a fresh app per test with different settings, and production builds one through Gunicorn (`nexus:create_app()`).

`Settings` fails loudly at start-up: no `SECRET_KEY` default, HubSpot needs its token, production refuses SQLite (Cloud Run's disk is ephemeral) and requires `INTERNAL_TOKEN`. A misconfigured deploy never boots, instead of misbehaving later.

## 2. Database — `nexus/db.py`, `nexus/models.py`, `migrations/`

No Flask-SQLAlchemy: the engine and `sessionmaker` live in `app.extensions`, and `get_session()` opens one session per request in `flask.g`, closed on teardown. That is all Flask-SQLAlchemy does for you; here you can see it.

Model decisions:
- `Promoter.public_id` is the `ref` in the link: random, immutable, unique. The name can change; attribution never breaks.
- No delete for promoters, only `archived_at`.
- `Lead.email` is unique: one person, one lead, first attribution wins.
- Timestamps are naive UTC everywhere (`utcnow()`), so SQLite and Postgres behave the same.

Schema changes only through Alembic. `tests/test_migrations.py` compares the migrated schema with the models, so forgetting a migration fails CI.

## 3. Auth — `nexus/security.py`, `blueprints/auth.py`

- Session = signed cookie with `uid` + `session_version`. Changing a password or deactivating a user bumps `session_version`, which kills every older cookie: revocation without a sessions table.
- Login checks a dummy hash when the e-mail does not exist, so response time does not reveal which e-mails are registered.
- `session.clear()` before login prevents session fixation.
- CSRF: Flask-WTF checks `X-CSRFToken` on every POST/PATCH. The SPA gets the token from `/api/auth/csrf`. `/internal/*` is exempt because it uses a bearer token, not cookies.

## 4. The core flow — `blueprints/public.py`, `outbox.py`, `crm/`

This is the heart of the project. Read `submit_lead()`:

1. Validate (Pydantic), drop bots (honeypot), short-circuit duplicates.
2. Insert the `Lead` **and** its `OutboxEvent` in the **same transaction**. Either both exist or neither does.
3. Commit. From here the lead is safe even if the CRM is on fire.
4. Try the CRM once, right away (`process_event`). If it fails, the event stays `pending` with `next_attempt_at` pushed back (30 s, 1 min, 2 min… 6 h).
5. `flush()` — called by Cloud Scheduler every 5 min — retries due events. On Postgres it uses `FOR UPDATE SKIP LOCKED`, so two overlapping runs split the work instead of double-sending.

Because a retry can follow a success whose response got lost, delivery is **at-least-once**. That is why `CRMProvider.upsert_lead` must be idempotent: HubSpot answers `409` for an existing e-mail and the adapter turns it into an update.

Errors are classified: transient (429, 5xx, network, and 401/403 because a fixed token will fix them) are retried; any other 4xx goes straight to `failed`, and an admin can re-queue it.

## 5. Dashboards — `blueprints/dashboard.py`

All numbers come from Nexus's own tables, never from the CRM. The leaderboard is one SQL query: `promoters LEFT JOIN leads ON (promoter match AND created_at >= start)`. The date filter is in the `ON` clause on purpose — in a `WHERE` it would drop promoters with zero leads.

Periods start at local midnight of the viewer's time zone (`tz` query param, default UTC), converted to UTC for the query.

## 6. Frontend — `frontend/src/`

- `api.ts`: fetch wrapper; CSRF token handling; typed errors with field messages.
- `app-context.tsx`: loads `/api/config` (brand) and `/api/auth/me` once.
- `i18n.tsx`: typed EN/ES dictionaries.
- `pages/`: one file per screen. Routing in `main.tsx`; `RequireUser` guards private routes.
- The brand color is a CSS variable set at runtime from `/api/config`, mapped to Tailwind's `brand` color — one build for every white-label deployment.

## 7. Running it

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Linux/macOS: .venv/bin/pip
cp .env.example .env                                            # set SECRET_KEY
flask --app nexus migrate && flask --app nexus seed-demo
cd frontend && npm ci && npm run build && cd ..
flask --app nexus run                                           # http://127.0.0.1:5000
```

For frontend work, run `flask --app nexus run` and `npm run dev` in `frontend/` (Vite on :5173 proxies `/api`).

## Exercises to own the code

1. Add a `source` field to `Lead` (e.g. "instagram") — model, Alembic migration, API, form. `test_migrations_match_models` will tell you if you forget the migration.
2. Write a `ZohoProvider` implementing `CRMProvider`, with tests using `responses`.
3. Add a per-promoter detail page: leads per day for the last 30 days (one `GROUP BY date` query).
4. Move the rate-limit storage to Redis and explain why it matters with several Cloud Run instances.
