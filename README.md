# DevFolio — Backend API

A production-minded **Django REST Framework** API powering a single-owner developer portfolio and blog. It exposes a clean, filterable, paginated REST API with JWT authentication, granular permissions, request throttling, a non-double-counting view counter, comment moderation, a contact inbox, and an owner analytics dashboard.

> **Single-owner by design.** There is exactly one privileged user — the site owner (a Django superuser). There is **no registration endpoint** anywhere. Everyone else is an anonymous visitor who can read public content, like posts, comment (held for moderation), and send contact messages.

---

## Tech stack

| Concern | Choice |
|---|---|
| Language / framework | Python 3.11+ · Django 5.2 |
| API | Django REST Framework 3.15+ |
| Auth | `djangorestframework-simplejwt` (access + refresh, rotation + blacklist) |
| Filtering | `django-filter` |
| CORS | `django-cors-headers` |
| Images | Pillow |
| Config | `python-decouple` (`.env`) |
| Database | SQLite by default · PostgreSQL optional via env |

---

## Quick start

```bash
cd portfolio-backend

# 1. Create & activate a virtualenv
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env              # then edit if needed (defaults work for local dev)

# 4. Migrate the database
python manage.py migrate

# 5. Seed realistic demo content (+ demo owner account)
python manage.py seed_demo

# 6. Run the server
python manage.py runserver
```

API base URL: **`http://127.0.0.1:8000/api/`** · Admin: **`http://127.0.0.1:8000/admin/`**

### Demo owner credentials (created by `seed_demo`)

```
username: owner
password: DevFolioDemo!2026
```

> Replace the seeded content with your own via the dashboard or Django admin. Change this password before deploying anywhere public.

---

## Environment variables (`.env`)

| Key | Default | Notes |
|---|---|---|
| `SECRET_KEY` | — | Long random string (required) |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,...` | Frontend origin(s) only — never allow-all |
| `DB_ENGINE` | `sqlite` | Or `postgres` (+ `DB_NAME/USER/PASSWORD/HOST/PORT`) |
| `DEFAULT_FROM_EMAIL` | `noreply@devfolio.local` | Sender for notification emails |
| `OWNER_NOTIFY_EMAIL` | `owner@devfolio.local` | Where new-comment notices go (console backend in dev) |

The real `.env` is git-ignored. `.env.example` documents every key.

---

## Data model

Eleven models across four areas:

- **Profile** *(singleton)* — name, headline, bio, contact, socials, avatar, resume, availability.
- **Portfolio** — `Skill` (category + proficiency), `Experience`, `Education`, `Project` (slug, tech-stack M2M → Skill, cover image).
- **Blog** — `Category`, `Tag`, `Post` (slug, draft/published, auto reading-time, view counter), `Comment` (one-level replies, moderated), `PostLike` (one per visitor per post).
- **Contact** — `ContactMessage` (read/unread inbox).

Highlights: automatic unique slugs, singleton enforcement on `Profile`, reading-time computed on save, `published_at` stamped once on first publish, and one-level-only comment replies enforced in the model.

---

## API reference

Base path: `/api/`. Public reads need no auth; **all writes to portfolio/blog content require the owner bearer token**.

### Auth
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/login/` | public | Returns `access` + `refresh` (+ user) |
| POST | `/auth/refresh/` | public | New access token from refresh |
| POST | `/auth/logout/` | owner | Blacklists the refresh token |
| GET | `/auth/me/` | owner | Current user (restore session) |
| POST | `/auth/change-password/` | owner | Change password |
| — | `/auth/register/` | — | **Does not exist → 404 by design** |

### Profile & Portfolio
| Method | Path | Access |
|---|---|---|
| GET / PATCH | `/profile/` | public / owner |
| GET · POST/PATCH/DELETE | `/skills/` `/skills/{id}/` | public · owner |
| GET · POST/PATCH/DELETE | `/experiences/` | public · owner |
| GET · POST/PATCH/DELETE | `/education/` | public · owner |
| GET · POST/PATCH/DELETE | `/projects/` `/projects/{slug}/` | public · owner |

Filters: `skills?category=&is_featured=`, `projects?category=&is_featured=&tech=`.

### Blog
| Method | Path | Access | Notes |
|---|---|---|---|
| GET · write | `/categories/` `/tags/` | public · owner | |
| GET | `/posts/` | public | Published only; `?search=&category=&tag=&is_featured=` |
| GET | `/posts/?status=DRAFT` | owner | Drafts visible to owner only |
| GET | `/posts/{slug}/` | public | Drafts → 404 for non-owners; increments views (deduped) |
| POST/PATCH/DELETE | `/posts/` `/posts/{slug}/` | owner | |
| POST | `/posts/{slug}/like/` | public | Toggle; requires `X-Visitor-Id` header |
| GET | `/posts/{slug}/comments/` | public | Approved comments, threaded |
| POST | `/posts/{slug}/comments/` | public | Held for moderation (throttled) |
| GET/PATCH/DELETE | `/comments/` `/comments/{id}/` | owner | Moderation queue (`?is_approved=`) |

### Contact & Dashboard
| Method | Path | Access |
|---|---|---|
| POST | `/contact/` | public (throttled) |
| GET/PATCH/DELETE | `/contact/` `/contact/{id}/` | owner (`?is_read=`) |
| GET | `/dashboard/stats/` | owner |

`/dashboard/stats/` returns totals, top posts by views, recent comments, and a zero-filled 6-month posts-per-month series — all computed with ORM aggregation.

---

## Security & correctness features

- **JWT** with short access + long refresh tokens, rotation, and refresh-token **blacklisting** on logout.
- **`IsOwnerOrReadOnly`** default permission — safe methods open, writes owner-only (superuser). Enforced server-side, not just in the UI.
- **Throttling** — anon reads, plus stricter scoped limits: comments `5/hour`, contact `3/hour`, likes `30/min`.
- **View counter** that never double-counts: a per-visitor cache cooldown + atomic `F()` update, and the owner's own views are ignored.
- **Draft & moderation privacy** — drafts and unapproved comments never appear in public responses; commenter emails are never exposed publicly.
- **Absolute media URLs** in responses; **CORS** limited to configured origins with the custom `X-Visitor-Id` header allow-listed.
- Request-timing middleware adds `X-Response-Time` and logs `METHOD /path -> status (ms)`.
- New-comment notifications emailed to the owner (console backend in dev).

---

## Testing the API

**Postman:** import `DevFolio.postman_collection.json`. Run **Auth → Login (owner)** first; it auto-saves the tokens so every owner request is authorized.

**Acceptance checks** (with the server running and data seeded):

```bash
bash acceptance_test.sh
```

This verifies the spec's core guarantees: visitors get `401` on writes, non-owners get `403`, `/auth/register/` is `404`, drafts return `404` publicly but `200` for the owner, unapproved comments are hidden, and the like endpoint toggles idempotently.

Django's own system checks:

```bash
python manage.py check
```

---

## Project layout

```
portfolio-backend/
├── config/            # settings, root urls, wsgi/asgi
├── api/
│   ├── models.py      # 11 models
│   ├── serializers.py # validation lives here
│   ├── views.py       # viewsets + auth + dashboard
│   ├── permissions.py # IsOwnerOrReadOnly / IsOwner
│   ├── filters.py throttles.py pagination.py
│   ├── middleware.py signals.py validators.py
│   ├── admin.py       # all models registered
│   └── management/commands/seed_demo.py
├── requirements.txt
├── .env.example
└── DevFolio.postman_collection.json
```

---

## Notes for deployment

Set `DEBUG=False`, a strong `SECRET_KEY`, real `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`, switch `DB_ENGINE=postgres`, run `python manage.py collectstatic`, serve media through your web server or object storage, and swap the console email backend for a real SMTP provider.
