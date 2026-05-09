# LeadForge — Full Audit Fix Prompt for Claude Code

> **Instructions for Claude Code**: Work through every phase sequentially. Do not skip ahead.
> After each edit, run the verification command listed. If it fails, fix it before proceeding.
> The stack must not be started until Phase 3. Some verifications are static (grep/read),
> others are live (curl). They are labelled clearly.

---

## Context

You are fixing a Python/Next.js lead generation app. The repo root has:
- `backend/` — FastAPI + Celery + SQLAlchemy
- `scraper/` — ScrapeGraphAI-based scraper (separate package, mounted at `/scraper` in Docker)
- `frontend/` — Next.js 14
- `docker-compose.yml` — orchestrates all services

Eight bugs were found in an audit. Fix them in the exact order below.
Dependency order matters: later fixes build on earlier ones.

---

## Phase 1 — Static Code Fixes (no Docker needed)

### Fix 1 · Wrong import path in Celery task

**File**: `backend/app/workers/tasks.py`

Find this line (around line 83, inside the `scrape_source_task` function):
```python
from app.scraper.engine import ScraperEngine
```

Replace it with:
```python
from scraper.engine import ScraperEngine
```

**Why**: The `scraper/` package lives at repo root, not inside `backend/app/`. The Docker
volume mounts it at `/scraper`, but `app.scraper` is not a valid Python path — this import
raises `ModuleNotFoundError` on every scrape job execution.

**Verify (static)**:
```bash
grep -n "from scraper.engine import ScraperEngine" backend/app/workers/tasks.py
```
Expected output: a line number followed by the correct import. If empty, the edit didn't save.

---

### Fix 2 · Add `/scraper` to PYTHONPATH in Dockerfile

**File**: `backend/Dockerfile`

After the `WORKDIR /app` line, add:
```dockerfile
ENV PYTHONPATH="/scraper:${PYTHONPATH}"
```

The full top of the file should now read:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH="/scraper:${PYTHONPATH}"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget gnupg \
    && rm -rf /var/lib/apt/lists/*
```

**Why**: Without this, even though `./scraper` is mounted at `/scraper` inside the container,
Python's import system doesn't know to look there. Both the `backend` and `worker` services
use this same Dockerfile, so both get fixed with one change.

**Verify (static)**:
```bash
grep -n "PYTHONPATH" backend/Dockerfile
```
Expected: `ENV PYTHONPATH="/scraper:${PYTHONPATH}"`

---

### Fix 3 · Create concrete CustomScraper (replace abstract in registry)

**File**: `scraper/scrapers/base.py`

At the **bottom** of the file, after the `BaseScraper` class definition, append:

```python

class CustomScraper(BaseScraper):
    """Concrete scraper for arbitrary / unrecognised job board URLs.

    Used as the fallback when the URL doesn't match any known platform.
    Applies a generic extraction prompt suitable for most job listing pages.
    """

    platform: str = "custom"

    PROMPT: str = (
        "Extract all job listings from this page. For each job, extract:\n"
        "- title: Job title\n"
        "- company: Company name\n"
        "- location: Job location if available\n"
        "- salary: Salary information if available\n"
        "- description: Full job description or summary\n"
        "- requirements: Key requirements or qualifications\n"
        "- url: Direct link to the job posting\n"
        "- skills: List of required skills if mentioned\n\n"
        "Return a JSON array of job objects. If no jobs found, return []."
    )

    def get_prompt(self) -> str:
        """Return the generic extraction prompt."""
        return self.PROMPT
```

**File**: `scraper/scrapers/__init__.py`

Update the import and registry entry:

```python
"""Platform-specific scraper registry."""

from scraper.scrapers.base import BaseScraper, CustomScraper
from scraper.scrapers.linkedin import LinkedInScraper
from scraper.scrapers.naukri import NaukriScraper
from scraper.scrapers.upwork import UpWorkScraper
from scraper.scrapers.indeed import IndeedScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "upwork": UpWorkScraper,
    "indeed": IndeedScraper,
    "custom": CustomScraper,  # concrete class — was BaseScraper (abstract), which caused TypeError
}

__all__ = [
    "SCRAPER_REGISTRY",
    "BaseScraper",
    "CustomScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "UpWorkScraper",
    "IndeedScraper",
]
```

**Why**: `BaseScraper` is abstract (`@abstractmethod get_prompt`). Putting it in the registry
causes `TypeError: Can't instantiate abstract class BaseScraper` the moment any URL hits the
"custom" fallback path. A concrete subclass with a real `get_prompt` fixes this.

**Verify (static)**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'scraper')
from scraper.scrapers import SCRAPER_REGISTRY
custom = SCRAPER_REGISTRY['custom']
inst = custom()
print('OK — CustomScraper instantiated, prompt length:', len(inst.get_prompt()))
"
```
Expected: `OK — CustomScraper instantiated, prompt length: <some number>`
If you get `TypeError` or `ImportError`, re-check Fix 1 and Fix 3.

---

### Fix 4 · Add URL deduplication to the scrape task

**File**: `backend/app/workers/tasks.py`

Inside `scrape_source_task`, find the inner `for item in scraped_items:` loop.
Before the `lead = Lead(...)` instantiation, add a dedup check.

Replace the loop body from:
```python
            for item in scraped_items:
                lead_data = {
```

To:
```python
            for item in scraped_items:
                # ── Layer 1 dedup: URL exact match ──────────────────────
                item_url = item.get("url", "").strip()
                if item_url:
                    existing = db.execute(
                        select(Lead).where(Lead.url == item_url)
                    ).scalar_one_or_none()
                    if existing is not None:
                        logger.debug(
                            "Skipping duplicate lead url=%s", item_url
                        )
                        continue

                lead_data = {
```

Make sure the indentation matches the surrounding code (12 spaces inside the `try` block,
inside the `with SyncSessionLocal()` block).

**Also** add `select` to the existing imports at the top of `tasks.py` if not already present:
```python
from sqlalchemy import select
```
(It's already imported — just confirm it's there.)

**Why**: Without this check, every scheduled scrape re-inserts every listing. After one week
of 6-hourly runs, there would be 28 copies of every job. This layer 1 (URL-based) dedup
eliminates ~80% of duplicates cheaply, before any LLM calls.

**Verify (static)**:
```bash
grep -n "Skipping duplicate lead" backend/app/workers/tasks.py
```
Expected: a line with the log message inside the task function.

---

### Fix 5 · Add unique constraint to Lead.url

**File**: `backend/app/models/lead.py`

Find the `url` column definition:
```python
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
```

Replace with:
```python
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
```

**Why**: The application-level dedup check (Fix 4) handles normal flow. The `unique=True`
constraint is the database-level safety net that prevents duplicates even under race
conditions (e.g., two workers scraping the same source simultaneously).

The `index=True` makes the URL lookup in Fix 4 fast — without it, every dedup check is
a full table scan.

**Note**: This requires an Alembic migration. That is handled in Phase 2.

**Verify (static)**:
```bash
grep -A5 "url: Mapped\[str\]" backend/app/models/lead.py | grep "unique"
```
Expected: `unique=True,`

---

### Fix 6 · Wire rate limiter into the scraper engine

**File**: `scraper/engine.py`

At the top of the file, add this import after the existing imports:
```python
from scraper.utils.rate_limiter import RateLimiter
```

In the `ScraperEngine.__init__` method, after `self.config = config or ScraperConfig()`,
add:
```python
        self._rate_limiter = RateLimiter(default_rate=1.0)
        # Per-platform conservative limits — these sites block aggressive scrapers
        self._rate_limiter.set_rate("www.linkedin.com", 0.25)   # 1 req / 4s
        self._rate_limiter.set_rate("linkedin.com", 0.25)
        self._rate_limiter.set_rate("www.naukri.com", 0.5)      # 1 req / 2s
        self._rate_limiter.set_rate("naukri.com", 0.5)
        self._rate_limiter.set_rate("www.upwork.com", 0.33)     # 1 req / 3s
        self._rate_limiter.set_rate("upwork.com", 0.33)
        self._rate_limiter.set_rate("www.indeed.com", 0.5)
        self._rate_limiter.set_rate("indeed.com", 0.5)
```

At the top of `ScraperEngine.scrape()`, before the `from scraper.scrapers import ...` line,
add:
```python
        # Apply per-domain rate limit before any network activity
        from urllib.parse import urlparse as _urlparse
        _domain = _urlparse(url).hostname or "unknown"
        self._rate_limiter.acquire(_domain)
        logger.info(f"Rate limit cleared for domain={_domain}")
```

**Why**: `RateLimiter` was fully implemented (`scraper/utils/rate_limiter.py`) but never
called. LinkedIn and Upwork will return 429 or serve bot-detection pages without pacing.
The per-domain token bucket was specifically built for this — it just wasn't wired up.

**Verify (static)**:
```bash
grep -n "_rate_limiter" scraper/engine.py | head -10
```
Expected: multiple lines showing initialisation and the `acquire` call.

---

### Fix 7 · Fix login — send form-encoded body with `username` field

**File**: `frontend/src/lib/auth.ts`

Find the `login` function:
```typescript
export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
    email,
    password,
  });
```

Replace with:
```typescript
export async function login(email: string, password: string): Promise<LoginResponse> {
  // FastAPI's OAuth2PasswordRequestForm requires application/x-www-form-urlencoded
  // with field name "username" (OAuth2 spec), not a JSON body with "email".
  const formData = new URLSearchParams();
  formData.append('username', email);   // NOTE: field must be "username" per OAuth2 spec
  formData.append('password', password);

  const { data } = await import('./api').then(m => m.default).then(axiosInstance =>
    axiosInstance.post<LoginResponse>('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  );
```

Wait — that dynamic import pattern is awkward. Use this cleaner version instead.
Replace the entire `login` function:

```typescript
export async function login(email: string, password: string): Promise<LoginResponse> {
  // FastAPI OAuth2PasswordRequestForm requires form-encoded data, NOT JSON.
  // The field name must be "username" (OAuth2 spec — even if it holds an email).
  const formData = new URLSearchParams({
    username: email,
    password: password,
  });

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  const data: LoginResponse = await response.json();

  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }
  }

  return data;
}
```

**Why**: FastAPI's `OAuth2PasswordRequestForm` decodes `application/x-www-form-urlencoded`
body with a field named `username`. Sending JSON causes FastAPI to return 422 Unprocessable
Entity before any authentication logic runs. Every login attempt was failing silently.

**Verify (static)**:
```bash
grep -n "URLSearchParams\|username.*email\|form-urlencoded" frontend/src/lib/auth.ts
```
Expected: lines showing the URLSearchParams usage and the `username: email` mapping.

---

### Fix 8 · Add dynamic per-source scheduling to Celery beat

**File**: `backend/app/workers/celery_app.py`

At the top, add this import after the existing imports:
```python
from celery.schedules import crontab
```
(Already imported — confirm it's there.)

At the **bottom** of `celery_app.py`, after `celery_app.autodiscover_tasks(...)`, add:

```python

# ---------------------------------------------------------------------------
# Dynamic per-source periodic scheduling
# ---------------------------------------------------------------------------
# On worker startup, read active JobSource rows from DB and register a
# periodic scrape task for each one using its schedule_cron field.
# New sources added via the API will be picked up on the next worker restart
# or after a SIGHUP. For fully dynamic scheduling without restarts,
# consider migrating to django-celery-beat in a future iteration.
# ---------------------------------------------------------------------------

@celery_app.on_after_finalize.connect
def setup_source_schedules(sender, **kwargs):
    """Register a periodic scrape task for every active JobSource."""
    try:
        import os
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        sync_url = os.environ.get("DATABASE_SYNC_URL", "")
        if not sync_url:
            import logging
            logging.getLogger(__name__).warning(
                "DATABASE_SYNC_URL not set — skipping dynamic source scheduling"
            )
            return

        engine = create_engine(sync_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Raw query to avoid importing ORM models at celery startup
            # (which can trigger async engine initialisation prematurely)
            rows = session.execute(
                text(
                    "SELECT id, name, schedule_cron FROM job_sources "
                    "WHERE is_active = true AND schedule_cron IS NOT NULL"
                )
            ).fetchall()

        for row in rows:
            source_id, name, cron_str = row

            # Parse "minute hour day month weekday" cron string
            parts = cron_str.strip().split()
            if len(parts) != 5:
                continue  # skip malformed cron strings

            minute, hour, day_of_month, month, day_of_week = parts

            sender.add_periodic_task(
                crontab(
                    minute=minute,
                    hour=hour,
                    day_of_month=day_of_month,
                    month_of_year=month,
                    day_of_week=day_of_week,
                ),
                sender.signature(
                    "app.workers.tasks.scrape_source_task",
                    args=[str(source_id)],
                ),
                name=f"auto-scrape-{name}-{source_id}",
            )

        engine.dispose()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Failed to set up dynamic source schedules: %s", exc
        )
        # Don't raise — beat must start even if DB is temporarily unavailable
```

**Why**: The `schedule_cron` field exists on `JobSource` but was never read by the beat
scheduler. All scheduled scraping was architecturally present but functionally absent.
This reads active sources from Postgres on beat startup and registers one periodic task
per source. The raw SQL query avoids importing the async ORM at Celery import time.

**Verify (static)**:
```bash
grep -n "setup_source_schedules\|on_after_finalize" backend/app/workers/celery_app.py
```
Expected: lines showing both the decorator and function definition.

---

## Phase 2 — Configuration Fixes

### Fix 9 · Add `DATABASE_SYNC_URL` to all backend services in docker-compose

**File**: `docker-compose.yml`

The `backend`, `worker`, and `beat` services all need `DATABASE_SYNC_URL`. Find each
service's `environment:` section and add the missing variable.

For the `backend` service, the environment block should become:
```yaml
    environment:
      - DATABASE_URL=postgresql+asyncpg://leadforge:leadforge@db:5432/leadforge
      - DATABASE_SYNC_URL=postgresql://leadforge:leadforge@db:5432/leadforge
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
```

For the `worker` service:
```yaml
    environment:
      - DATABASE_URL=postgresql+asyncpg://leadforge:leadforge@db:5432/leadforge
      - DATABASE_SYNC_URL=postgresql://leadforge:leadforge@db:5432/leadforge
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
```

For the `beat` service:
```yaml
    environment:
      - DATABASE_URL=postgresql+asyncpg://leadforge:leadforge@db:5432/leadforge
      - DATABASE_SYNC_URL=postgresql://leadforge:leadforge@db:5432/leadforge
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**Why**: `database.py` reads `DATABASE_SYNC_URL` at module import time to create
`SyncSessionLocal`. This runs when any module in `backend/app/` is imported — including
at Celery worker startup. Without this env var, Pydantic-settings raises `ValidationError`
and the worker container exits immediately after starting.

**Verify (static)**:
```bash
grep -c "DATABASE_SYNC_URL" docker-compose.yml
```
Expected: `3` (one per service — backend, worker, beat)

---

### Fix 10 · Fix scoring loop — batch scores with one event loop

**File**: `backend/app/workers/tasks.py`

The current code calls `_run_async(scoring_service.score_lead(...))` inside a `for` loop,
creating and destroying an event loop (and its connection pool) for every single lead.

Replace the entire ingest loop in `scrape_source_task` — from after `scoring_service = LeadScoringService()` 
to before `# ── Finalise the job ──` — with:

```python
            # ── Ingest leads and collect lead_data for batch scoring ────
            leads_to_score: list[tuple] = []  # (Lead ORM object, lead_data dict)

            for item in scraped_items:
                # ── Layer 1 dedup: URL exact match ──────────────────────
                item_url = item.get("url", "").strip()
                if item_url:
                    existing = db.execute(
                        select(Lead).where(Lead.url == item_url)
                    ).scalar_one_or_none()
                    if existing is not None:
                        logger.debug("Skipping duplicate lead url=%s", item_url)
                        continue

                lead_data = {
                    "title": item.get("title", ""),
                    "company": item.get("company", ""),
                    "location": item.get("location", ""),
                    "salary": item.get("salary", ""),
                    "description": item.get("description", ""),
                    "requirements": item.get("requirements", ""),
                    "platform": source.platform.value
                    if hasattr(source.platform, "value")
                    else str(source.platform),
                }

                lead = Lead(
                    source_id=source_uuid,
                    platform=lead_data["platform"],
                    title=lead_data["title"],
                    company=lead_data["company"],
                    location=lead_data["location"],
                    salary=lead_data["salary"],
                    description=lead_data["description"],
                    requirements=lead_data["requirements"],
                    url=item_url,
                    raw_data=item.get("raw_data", {}),
                    contact_info=item.get("contact_info", {}),
                    status=LeadStatus.new,
                )
                db.add(lead)
                db.flush()
                leads_to_score.append((lead, lead_data))

            # ── Batch score all new leads in a single event loop ────────
            leads_created = 0
            if leads_to_score:
                try:
                    all_lead_data = [ld for _, ld in leads_to_score]
                    user_prefs = source.scrape_config.get("user_preferences")
                    scores = _run_async(
                        scoring_service.score_leads_batch(
                            all_lead_data,
                            user_preferences=user_prefs,
                        )
                    )
                    for (lead, _), score in zip(leads_to_score, scores):
                        lead.score = score
                except Exception as exc:
                    logger.warning("Batch scoring failed: %s — defaulting all to 50", exc)
                    for lead, _ in leads_to_score:
                        lead.score = 50.0

                leads_created = len(leads_to_score)
```

**Why**: The original code opened and closed an event loop per lead, destroying the
`AsyncOpenAI` client's connection pool each time. `score_leads_batch` already exists
and runs sequentially, but using it means one event loop handles all API calls — proper
keep-alive, connection reuse, no repeated TLS handshakes.

**Verify (static)**:
```bash
grep -n "score_leads_batch\|leads_to_score" backend/app/workers/tasks.py
```
Expected: multiple lines showing the batch pattern.

---

## Phase 3 — Build, Migrate, Run

### Step 3.1 · Create the `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:
```
OPENAI_API_KEY=sk-your-actual-key
JWT_SECRET=change-this-to-a-random-64-char-string-right-now
DATABASE_SYNC_URL=postgresql://leadforge:leadforge@localhost:5432/leadforge
```

Generate a safe JWT secret with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Paste the output as `JWT_SECRET`.

---

### Step 3.2 · Build all containers

```bash
docker compose build --no-cache
```

Watch for build errors. Both `backend` and `worker` use the same Dockerfile — the
`PYTHONPATH` fix from Fix 2 should appear in the build output.

**Verify**: No `ERROR` lines in build output.

---

### Step 3.3 · Start the database and Redis only first

```bash
docker compose up -d db redis
```

Wait for them to be healthy:
```bash
docker compose ps
```
Expected: both `leadforge-db` and `leadforge-redis` show `healthy`.

---

### Step 3.4 · Generate and apply the Alembic migration

The `Lead.url` unique constraint (Fix 5) requires a DB migration.

First, check for any existing duplicate URLs that would block the unique constraint:
```bash
docker compose exec db psql -U leadforge -d leadforge -c "
SELECT url, COUNT(*) as cnt FROM leads GROUP BY url HAVING COUNT(*) > 1;
"
```
If any rows appear, remove the duplicates:
```bash
docker compose exec db psql -U leadforge -d leadforge -c "
DELETE FROM leads WHERE id NOT IN (
  SELECT MIN(id) FROM leads GROUP BY url
);
"
```

Now generate the migration from inside the backend container:
```bash
docker compose run --rm backend alembic revision --autogenerate -m "add_unique_url_and_url_index_to_leads"
```

Inspect the generated file in `backend/alembic/versions/`. Confirm it contains:
- `op.create_unique_constraint(...)` on `leads.url`
- `op.create_index(...)` on `leads.url`

If the autogenerated migration looks correct, apply it:
```bash
docker compose run --rm backend alembic upgrade head
```

**Verify**:
```bash
docker compose exec db psql -U leadforge -d leadforge -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'leads' AND indexdef LIKE '%url%';
"
```
Expected: at least one row showing a unique index on `url`.

---

### Step 3.5 · Start all services

```bash
docker compose up -d
```

Wait ~15 seconds, then check all containers are running:
```bash
docker compose ps
```
Expected: all 6 services (`db`, `redis`, `backend`, `worker`, `beat`, `frontend`) show
`running` or `healthy`. If any show `exited`, read their logs:
```bash
docker compose logs <service-name> --tail=50
```

---

## Phase 4 — Runtime Verification

### Verify A · Health check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
Expected:
```json
{
    "status": "healthy",
    "version": "0.1.0"
}
```

### Verify B · Readiness (confirms DB + Redis connectivity)

```bash
curl -s http://localhost:8000/ready | python3 -m json.tool
```
Expected:
```json
{
    "status": "ready",
    "checks": {
        "database": true,
        "redis": true
    }
}
```
If `"database": false`, check `docker compose logs backend` for connection errors.

---

### Verify C · Login works (the Fix 7 test — critical)

Register a test user:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@leadforge.dev","password":"TestPass123!","full_name":"Test User"}' \
  | python3 -m json.tool
```
Expected: a user object with `id`, `email`, `full_name`.

Now login using form-encoded data (mirrors what the fixed frontend sends):
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@leadforge.dev&password=TestPass123!" \
  | python3 -m json.tool
```
Expected:
```json
{
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
}
```

**Save the access token**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@leadforge.dev&password=TestPass123!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token saved: ${TOKEN:0:20}..."
```

If you get `422 Unprocessable Entity`, Fix 7 didn't apply correctly. Re-check `auth.ts`.
If you get `401`, the credentials don't match — re-register.

---

### Verify D · Create a job source

```bash
curl -s -X POST http://localhost:8000/api/v1/job-sources/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Naukri",
    "url": "https://www.naukri.com/python-developer-jobs",
    "platform": "naukri",
    "schedule_cron": "0 */6 * * *",
    "is_active": true,
    "scrape_config": {
      "user_preferences": {
        "desired_role": "Python Developer",
        "preferred_locations": ["Remote", "Mumbai"],
        "min_salary": "1000000",
        "skills": ["Python", "FastAPI", "LLM"],
        "experience_level": "mid"
      }
    }
  }' | python3 -m json.tool
```
Expected: a source object with an `id` field. Save the ID:
```bash
SOURCE_ID="<paste the id from above>"
```

---

### Verify E · Trigger a manual scrape and watch it run

```bash
curl -s -X POST "http://localhost:8000/api/v1/job-sources/$SOURCE_ID/scrape" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```
Expected: `{"status": "queued", "task_id": "..."}` or similar.

Watch the worker logs in real time:
```bash
docker compose logs worker -f
```

Look for these log lines in order:
1. `Starting scrape: platform=naukri, url=...` — engine started ✓
2. `Rate limit cleared for domain=www.naukri.com` — Fix 6 working ✓
3. `Scrape completed for ..., raw result keys:` — ScrapeGraphAI returned ✓
4. `Normalized N job listings` — results parsed ✓
5. `Skipping duplicate lead` (on second trigger only) — Fix 4 working ✓
6. `Scrape completed: source=..., leads=N` — task finished ✓

If you see `ModuleNotFoundError: No module named 'app.scraper'` → Fix 1 or Fix 2 didn't apply.
If you see `TypeError: Can't instantiate abstract class` → Fix 3 didn't apply.
If you see `ValidationError` on startup → Fix 9 (DATABASE_SYNC_URL) didn't apply.

---

### Verify F · Dedup works (run the same scrape twice)

Trigger the scrape a second time:
```bash
curl -s -X POST "http://localhost:8000/api/v1/job-sources/$SOURCE_ID/scrape" \
  -H "Authorization: Bearer $TOKEN"
```

Wait for it to complete (watch `docker compose logs worker -f`), then check the leads count:
```bash
curl -s "http://localhost:8000/api/v1/leads/?per_page=100" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total leads: {d[\"total\"]} — should be same as first run')"
```

The count should be the same (or very close) as after the first scrape. If it doubled,
Fix 4 or Fix 5 didn't work. Check for any `Skipping duplicate lead` lines in the worker log.

---

### Verify G · Check leads endpoint returns scored results

```bash
curl -s "http://localhost:8000/api/v1/leads/?sort_by=score&sort_order=desc&per_page=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Expected: paginated response with leads, each having:
- `score` between 0.0 and 100.0 (not 0.0, which would mean scoring failed)
- `status`: `"new"`
- `title`, `company` non-empty

---

### Verify H · Beat scheduler registered source schedules

```bash
docker compose logs beat --tail=30
```

Look for lines like:
```
[INFO] setup_source_schedules: registered periodic task auto-scrape-Test Naukri-<uuid>
```
or `beat: Starting...` followed by at least the cleanup task.

If you added a source with `schedule_cron: "0 */6 * * *"`, the beat process should show
it in its schedule. You may need to restart beat after adding the first source:
```bash
docker compose restart beat
docker compose logs beat --tail=20
```

---

## Phase 5 — Final Sanity Check

Run all verifications as a one-liner sequence:

```bash
# 1. Health
curl -sf http://localhost:8000/health > /dev/null && echo "✓ API healthy" || echo "✗ API down"

# 2. DB + Redis
curl -sf http://localhost:8000/ready | python3 -c "
import sys,json; d=json.load(sys.stdin)
ok = all(d['checks'].values())
print('✓ Infra ready' if ok else '✗ Infra degraded: ' + str(d['checks']))
"

# 3. Import path (inside worker container)
docker compose exec worker python3 -c "
from scraper.engine import ScraperEngine
print('✓ scraper import OK')
" 2>&1

# 4. Abstract class fix
docker compose exec worker python3 -c "
from scraper.scrapers import SCRAPER_REGISTRY
SCRAPER_REGISTRY['custom']()
print('✓ CustomScraper instantiates OK')
" 2>&1

# 5. Rate limiter wired
docker compose exec worker python3 -c "
from scraper.engine import ScraperEngine
e = ScraperEngine()
assert hasattr(e, '_rate_limiter'), 'rate limiter missing'
print('✓ Rate limiter wired in engine')
" 2>&1

# 6. Unique constraint on DB
docker compose exec db psql -U leadforge -d leadforge -q -c "
SELECT COUNT(*) FROM pg_indexes
WHERE tablename='leads' AND indexdef LIKE '%url%'
" | grep -q "1" && echo "✓ URL unique index exists" || echo "✗ URL unique index missing"
```

All 6 should print ✓. If any print ✗, revisit the corresponding fix phase.

---

## Summary of What Was Fixed

| # | Severity | File | Issue | Fix |
|---|---|---|---|---|
| 1 | CRITICAL | `tasks.py` | Wrong import path `app.scraper` | Changed to `scraper.engine` |
| 2 | CRITICAL | `Dockerfile` | `/scraper` not on PYTHONPATH | Added `ENV PYTHONPATH` |
| 3 | HIGH | `scrapers/__init__.py` | Abstract class in registry | Created `CustomScraper` |
| 4 | CRITICAL | `tasks.py` | Zero deduplication | URL lookup before insert |
| 5 | CRITICAL | `models/lead.py` | No unique constraint on url | Added `unique=True, index=True` + migration |
| 6 | MEDIUM | `engine.py` | Rate limiter built but unwired | Wired in `ScraperEngine.__init__` + `scrape()` |
| 7 | CRITICAL | `auth.ts` | Login sends JSON to form endpoint | Switched to `URLSearchParams` + `username` field |
| 8 | HIGH | `celery_app.py` | Beat never reads source schedules | `on_after_finalize` dynamic task registration |
| 9 | HIGH | `docker-compose.yml` | `DATABASE_SYNC_URL` missing from worker/beat | Added to all 3 services |
| 10 | MEDIUM | `tasks.py` | New event loop per lead in scoring | Batch scoring with single `_run_async` call |
