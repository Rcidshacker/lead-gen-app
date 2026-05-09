# LeadForge — Architecture Document

> **Version:** 0.1.0 (MVP)
> **Last Updated:** 2026-05-09
> **Status:** Implementation Complete

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Request Flow](#request-flow)
3. [Component Architecture](#component-architecture)
4. [Data Model](#data-model)
5. [API Design](#api-design)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Considerations](#performance-considerations)
9. [Scaling Strategy](#scaling-strategy)

---

## System Architecture

LeadForge is a distributed system composed of six containerised services communicating
over HTTP and a Redis message broker. The architecture follows a **microservice-inspired
monolith** pattern — services share a single codebase but run in separate processes
for isolation and independent scaling.

```
                         ┌─────────────────────────┐
                         │      USER BROWSER       │
                         │   http://localhost:3000  │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │    REVERSE PROXY        │
                         │    (Nginx / Caddy)      │
                         │    TLS Termination      │
                         └──────┬──────────┬───────┘
                                │          │
                    ┌───────────▼──┐  ┌─────▼──────────┐
                    │   FRONTEND   │  │    BACKEND      │
                    │   Next.js    │  │    FastAPI      │
                    │   :3000      │  │    :8000        │
                    └───────┬──────┘  └──┬────┬────┬───┘
                            │           │    │    │
                            │     ┌─────▼┐  │    │
                            │     │ Auth │  │    │
                            │     └──────┘  │    │
                            │  ┌────────▼───▼┐  │
                            │  │ Services    │  │
                            │  │ Layer       │  │
                            │  └──┬──────┬───┘  │
                            │     │      │      │
                   ┌────────┼─────┼──────┼──────┼──────────┐
                   │        │     │      │      │          │
            ┌──────▼──────┐│  ┌──▼──────▼──┐   │  ┌───────▼──────┐
            │ PostgreSQL  ││  │   Redis    │   │  │ Celery Worker │
            │ + pgvector  ││  │  :6379     │◄──┼──│  (N instances)│
            │ :5432       ││  │            │   │  │               │
            └─────────────┘│  │  · Queue   │   │  │ ┌───────────┐ │
                           │  │  · Cache   │   │  │ │ Scraper   │ │
                           │  │  · Results │   │  │ │ Engine    │ │
                           │  │            │   │  │ ├───────────┤ │
                           │  └────────────┘   │  │ │ScrapeGraph│ │
                           │                   │  │ │  AI       │ │
                           │  ┌────────────┐   │  │ ├───────────┤ │
                           │  │ Celery Beat│   │  │ │  OpenAI   │ │
                           │  │ (scheduler)│   │  │ │  GPT-4o   │ │
                           │  └────────────┘   │  │ └─────┬─────┘ │
                           │                   │  └───────┼───────┘
                           │                   │          │
                           │          ┌────────▼────────▼────────┐
                           │          │    JOB BOARD SITES       │
                           │          │  LinkedIn · Naukri       │
                           │          │  UpWork · Indeed         │
                           │          │  Custom URLs            │
                           │          └─────────────────────────┘
```

### Service Summary

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **Frontend** | Next.js 14 | 3000 | Serves the SPA, handles client-side routing |
| **Backend** | FastAPI + Uvicorn | 8000 | REST API, authentication, business logic |
| **PostgreSQL** | pgvector/pgvector:pg16 | 5432 | Primary data store with vector extension |
| **Redis** | redis:7-alpine | 6379 | Message broker, task results, caching |
| **Celery Worker** | Celery 5.3 | — | Executes async scraping and scoring tasks |
| **Celery Beat** | Celery 5.3 | — | Periodic task scheduler (export cleanup) |

---

## Request Flow

### Scrape Job Lifecycle (Numbered Steps)

```
 1. User clicks "Scrape Now"
    ┌──────────────────────────────────────────────────────────────────────────────┐
    │ Browser                    Frontend               Backend              Redis │
    │   │                          │                      │                   │     │
    │   │── POST /api/v1/jobs ────►│                      │                   │     │
    │   │   {source_id, trigger}   │── POST /api/v1/jobs ►│                   │     │
    │   │                          │                      │                   │     │
 2. │                          │                      │── Create          │     │
    │                          │                      │   ScrapingJob     │     │
    │                          │                      │   (status=running)│     │
    │                          │                      │                   │     │
 3. │                          │                      │── celery.delay()──│──►  │
    │                          │                      │   scrape_source   │     │
    │                          │                      │   _task(id)       │     │
    │                          │                      │                   │     │
    │                          │◄── 202 Accepted ─────│                   │     │
    │                          │   {job_id, status}   │                   │     │
    │◄── job_id ───────────────│                      │                   │     │
    │   │                      │                      │                   │     │
    │                          │                      │          Worker  │     │
    │                          │                      │             │    │     │
 4. │                          │                      │             │◄───│──►  │
    │                          │                      │   Task picked    │     │
    │                          │                      │   up from queue  │     │
    │                          │                      │             │    │     │
 5. │                          │                      │             │    │     │
    │                          │                      │      ScraperEngine  │     │
    │                          │                      │      .scrape()      │     │
    │                          │                      │             │    │     │
 6. │                          │                      │             │    │     │
    │                          │                      │  ┌──────────▼──┐  │     │
    │                          │                      │  │ScrapeGraphAI│  │     │
    │                          │                      │  │ Playwright  │  │     │
    │                          │                      │  │   + LLM     │  │     │
    │                          │                      │  └──────┬─────┘  │     │
    │                          │                      │         │        │     │
 7. │                          │                      │         │        │     │
    │                          │                      │  ┌──────▼─────┐  │     │
    │                          │                      │  │  LinkedIn  │  │     │
    │                          │                      │  │  Naukri    │  │     │
    │                          │                      │  │  UpWork    │  │     │
    │                          │                      │  │  Indeed    │  │     │
    │                          │                      │  └──────┬─────┘  │     │
    │                          │                      │         │        │     │
    │                          │                      │  Normalised results   │
    │                          │                      │         │        │     │
 8. │                          │                      │  ┌──────▼─────┐  │     │
    │                          │                      │  │  Upsert    │  │     │
    │                          │                      │  │  Leads DB  │  │     │
    │                          │                      │  │  Score AI  │  │     │
    │                          │                      │  └──────┬─────┘  │     │
    │                          │                      │         │        │     │
 9. │── GET /api/v1/jobs/{id}─►│── GET /api/v1/jobs ─►│           │        │     │
    │   (polling every 5s)     │   /{id}              │◄─ status= │        │     │
    │                          │                      │  completed│        │     │
    │                          │◄── {status: "completed",  leads_found: 42} ───│
    │◄── leads list refresh ──│                      │           │        │     │
    └──────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Description

| Step | Actor | Action | Detail |
|------|-------|--------|--------|
| **1** | Browser → Frontend | User clicks "Scrape Now" | Frontend calls `POST /api/v1/jobs` with `source_id` |
| **2** | Backend | Create `ScrapingJob` record | Insert row with `status=running`, `started_at=now()` |
| **3** | Backend → Redis | Dispatch Celery task | `scrape_source_task.delay(source_id)` pushes to queue |
| **4** | Worker | Pick up task | Worker dequeues the task message from Redis |
| **5** | Worker | Detect platform | `ScraperEngine._detect_platform(url)` → e.g., `"linkedin"` |
| **6** | Worker → Job Site | Fetch and extract | ScrapeGraphAI renders page with Playwright, LLM extracts data |
| **7** | Worker | Normalise results | Raw output converted to uniform schema (title, company, etc.) |
| **8** | Worker → DB | Ingest and score leads | Insert Lead rows, call OpenAI for relevance score (0–100) |
| **9** | Frontend | Poll and refresh | TanStack Query polls `GET /jobs/{id}`; when `completed`, refetch leads |

---

## Component Architecture

### Frontend (Next.js)

The frontend is a **single-page application** built with Next.js 14 App Router. It
communicates exclusively with the backend REST API — no server-side data fetching
from the database.

#### Directory Structure

```
frontend/src/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root: QueryClientProvider, AppShell
│   ├── page.tsx                # Home → redirect to /dashboard
│   ├── globals.css             # Tailwind base + custom variables
│   ├── providers.tsx           # TanStack QueryClientProvider wrapper
│   ├── login/page.tsx          # Authentication page
│   ├── dashboard/page.tsx      # Dashboard: stats, charts, recent leads
│   ├── sources/page.tsx        # Job sources list view
│   ├── sources/[id]/page.tsx   # Source detail + edit
│   ├── leads/page.tsx          # Leads table with filters + pagination
│   ├── leads/[id]/page.tsx     # Lead detail view
│   ├── jobs/page.tsx           # Scraping job history
│   └── settings/page.tsx       # User settings
├── components/
│   ├── layout/                 # AppShell, Sidebar, Header
│   ├── ui/                     # Button, Card, Input, Table, Select, Badge, Modal
│   ├── dashboard/              # StatsGrid, RecentLeads, ScrapeActivity, LeadSourceChart
│   ├── leads/                  # LeadTable, LeadCard, LeadFilters, LeadScoreBadge
│   ├── sources/                # SourceCard, SourceForm
│   └── jobs/                   # JobList, JobStatusBadge
├── hooks/                      # TanStack Query hooks
│   ├── useLeads.ts             # useLeads(), useLead(), useUpdateLead()
│   ├── useSources.ts           # useSources(), useCreateSource()
│   ├── useJobs.ts              # useJobs(), useCreateJob()
│   └── useDashboard.ts         # useDashboardStats()
├── lib/
│   ├── api.ts                  # Axios instance + JWT interceptor
│   ├── auth.ts                 # Login, register, token storage (localStorage)
│   └── utils.ts                # cn(), formatDate(), formatSalary()
└── types/                      # TypeScript interfaces
    ├── lead.ts                 # Lead, LeadFilters
    ├── source.ts               # JobSource, PlatformType
    ├── job.ts                  # ScrapingJob, JobStatus
    └── dashboard.ts            # DashboardStats
```

#### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Data Fetching** | TanStack Query 5 | Manages server state with automatic caching, background refetching, and optimistic updates. Eliminates the need for Redux for API data. |
| **HTTP Client** | Axios | Interceptor support for JWT token injection, request/response transformation, and error handling. |
| **Charts** | Recharts | Declarative, composable chart components that render to SVG. Supports responsive containers. |
| **Icons** | Lucide React | Tree-shakeable SVG icon library with consistent 24px design. Zero runtime overhead for unused icons. |
| **Styling** | Tailwind CSS | Utility-first with `clsx` + `tailwind-merge` for conditional class composition. Design tokens in `tailwind.config.js`. |
| **Class Helper** | `cn()` from `clsx` + `tailwind-merge` | Safely merges Tailwind classes without specificity conflicts. Standard pattern from shadcn/ui. |

---

### Backend (FastAPI)

The backend is an async Python web application built with FastAPI. It serves the REST
API, manages authentication, and orchestrates business logic through a service layer.

#### Directory Structure

```
backend/app/
├── main.py                     # FastAPI app, lifespan, CORS, error handlers
├── config.py                   # Pydantic Settings (env vars)
├── database.py                 # Async + sync engines, session factories, Base
├── models/                     # SQLAlchemy ORM models
│   ├── user.py                 # User
│   ├── lead.py                 # Lead (pgvector embedding)
│   ├── job_source.py           # JobSource (PlatformType, ScrapeSchedule enums)
│   ├── scraping_job.py         # ScrapingJob (JobStatus enum)
│   └── export.py               # Export (ExportFormat enum)
├── schemas/                    # Pydantic v2 request/response schemas
│   ├── user.py                 # UserCreate, UserResponse, Token, TokenPayload
│   ├── lead.py                 # LeadCreate, LeadUpdate, LeadResponse
│   ├── job_source.py           # JobSourceCreate, JobSourceResponse
│   ├── scraping_job.py         # ScrapingJobResponse
│   └── export.py               # ExportCreate, ExportResponse
├── api/                        # Route handlers
│   ├── router.py               # Root APIRouter aggregation
│   ├── deps.py                 # JWT auth, password hashing, user dependencies
│   ├── auth.py                 # Register, login, /me
│   ├── leads.py                # Lead CRUD
│   ├── job_sources.py          # JobSource CRUD + scrape trigger
│   ├── scraping_jobs.py        # Job listing + status
│   ├── exports.py              # Export create + download
│   └── dashboard.py            # Aggregated statistics
├── services/                   # Business logic
│   ├── lead_scoring.py         # AI-powered relevance scoring
│   ├── export_service.py       # CSV/JSON file generation
│   └── webhook_service.py      # Outbound notifications
└── workers/                    # Celery
    ├── celery_app.py           # Celery config, beat schedule
    └── tasks.py                # 4 async tasks
```

#### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Pydantic Version** | v2 | 5–50x faster validation, stricter type checking, native `model_config` |
| **SQLAlchemy Style** | 2.0 async with `mapped_column` | Type-hinted ORM, async session support, no legacy `Column()` |
| **Dual Engines** | `AsyncEngine` + `Engine` | FastAPI uses async; Celery workers use sync (no event loop conflicts) |
| **Session Management** | `async_sessionmaker` / `sessionmaker` | Factory pattern — dependency injection via `get_db()` |
| **Migration Tool** | Alembic | Auto-generate migrations from model changes, versioned rollback |
| **Error Handling** | Global exception handlers | Consistent JSON error envelope across all endpoints |
| **CORS** | Environment-dependent | `allow_origins=["*"]` in dev, restricted to `FRONTEND_URL` in prod |

---

### Scraper Engine (ScrapeGraphAI)

The scraper engine is a standalone Python module that integrates with ScrapeGraphAI
for LLM-powered web scraping. It follows the Strategy Pattern — each platform has
a dedicated scraper class with a tailored extraction prompt.

#### Directory Structure

```
scraper/
├── __init__.py
├── requirements.txt           # scrapegraphai, playwright, loguru
├── engine.py                  # ScraperEngine (orchestrator + normaliser)
├── scrapers/
│   ├── __init__.py            # SCRAPER_REGISTRY
│   ├── base.py                # BaseScraper ABC
│   ├── linkedin.py            # LinkedInScraper
│   ├── naukri.py              # NaukriScraper
│   ├── upwork.py              # UpWorkScraper
│   └── indeed.py              # IndeedScraper
├── extractors/
│   ├── __init__.py
│   ├── job_extractor.py       # Field-level extraction helpers
│   └── contact_extractor.py   # Email/phone regex extraction
└── utils/
    ├── __init__.py
    ├── proxy_manager.py       # HTTP/SOCKS5 proxy rotation
    └── rate_limiter.py        # Token-bucket rate limiter
```

#### Scraping Strategies

| Platform | Scraper Class | LLM Prompt Focus | Special Fields Extracted |
|----------|---------------|------------------|--------------------------|
| **LinkedIn** | `LinkedInScraper` | Job listings from search results | `posted_date`, `skills` array |
| **Naukri** | `NaukriScraper` | Job listings with Indian market specifics | `experience` (years), `education` |
| **UpWork** | `UpWorkScraper` | Freelance project listings | `job_type` (fixed/hourly), `experience_level` |
| **Indeed** | `IndeedScraper` | Job listings with company ratings | `rating` (1–5), `remote` (boolean) |
| **Custom** | `BaseScraper` | Generic job listing extraction | None (generic schema only) |

#### Scraper Configuration

The scraper engine is configured via the `ScraperConfig` dataclass:

```python
@dataclass
class ScraperConfig:
    model: str           # LLM model (default: "gpt-4o-mini")
    temperature: float   # Sampling temperature (default: 0.1)
    headless: bool       # Browser headless mode (default: True)
    max_pages: int       # Max pages per source (default: 5)
    delay: int           # Inter-request delay in seconds (default: 2)
    timeout: int         # HTTP timeout in seconds (default: 30)
    verbose: bool        # ScrapeGraphAI verbose logging (default: True)
```

All settings can be overridden via environment variables (`SGAI_MODEL`,
`SGAI_TEMPERATURE`, `SCRAPER_DEFAULT_DELAY`, `SCRAPER_TIMEOUT`).

---

### Background Workers (Celery)

Celery workers execute long-running tasks asynchronously. The backend API dispatches
tasks to Redis, and one or more worker processes consume the queue.

#### Tasks

| Task Name | Trigger | Purpose | Retry Policy |
|-----------|---------|---------|-------------|
| `scrape_source_task` | User action or scheduled | Full scrape → ingest → score pipeline for a source | 3 retries, 60s back-off |
| `score_lead_task` | Manual re-score | Re-score a single lead via AI | No retry |
| `generate_export_task` | User action | Generate CSV/JSON export file | No retry |
| `cleanup_old_exports_task` | Celery Beat (daily 03:00 UTC) | Remove export files older than 7 days | No retry |

#### Celery Configuration

```python
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,      # One task per worker at a time
    task_acks_late=True,                # Acknowledge after completion
    task_reject_on_worker_lost=True,    # Re-queue if worker crashes
    task_track_started=True,            # Track "started" state
    result_extended=True,               # Include start time, args in result
)
```

#### Beat Schedule

```python
celery_app.conf.beat_schedule = {
    "cleanup-old-exports": {
        "task": "app.workers.tasks.cleanup_old_exports_task",
        "schedule": crontab(hour=3, minute=0),  # Daily at 03:00 UTC
    },
}
```

---

## Data Model

### ER Diagram

```
┌─────────────────────────┐          ┌─────────────────────────────┐
│         users           │          │        job_sources           │
├─────────────────────────┤          ├─────────────────────────────┤
│ ● id          UUID (PK) │◄────┐   │ ● id          UUID (PK)     │
│   email       VARCHAR    │     │   │   user_id     UUID (FK) ────┘
│   hashed_password VARCHAR │     │   │   name        VARCHAR       │
│   full_name   VARCHAR    │     │   │   platform    ENUM          │
│   is_active   BOOLEAN    │     │   │   url         TEXT          │
│   is_superuser BOOLEAN   │     │   │   scrape_config JSONB       │
│   created_at  TIMESTAMP  │     │   │   is_active   BOOLEAN       │
│   updated_at  TIMESTAMP  │     │   │   schedule    ENUM          │
└────────┬────────────────┘     │   │   last_scraped_at TIMESTAMP  │
         │                      │   │   created_at  TIMESTAMP      │
         │ 1:N                  │   │   updated_at  TIMESTAMP      │
         │                      │   └──────────────┬──────────────┘
         │                      │                  │
         │ 1:N                  │                  │ 1:N
┌────────▼────────────────┐     │   ┌──────────────▼──────────────┐
│        exports          │     │   │          leads               │
├─────────────────────────┤     │   ├─────────────────────────────┤
│ ● id          UUID (PK) │     │   │ ● id          UUID (PK)     │
│   user_id     UUID (FK)─┘     │   │   source_id   UUID (FK) ────┘
│   format      ENUM            │   │   platform    VARCHAR        │
│   filters     JSONB           │   │   title       VARCHAR        │
│   file_url    VARCHAR         │   │   company     VARCHAR        │
│   created_at  TIMESTAMP       │   │   location    VARCHAR        │
└─────────────────────────────┘   │   │   salary      VARCHAR        │
                                  │   │   description TEXT           │
                                  │   │   requirements TEXT           │
                                  │   │   contact_info JSONB          │
                                  │   │   url         TEXT            │
                                  │   │   raw_data    JSONB           │
                                  │   │   score       FLOAT           │
                                  │   │   status      ENUM            │
                                  │   │   embedding   VECTOR(1536)    │
                                  │   │   created_at  TIMESTAMP       │
                                  │   │   updated_at  TIMESTAMP       │
                                  │   └──────────────┬──────────────┘
                                  │                  │
                                  │                  │ 1:N
                                  │   ┌──────────────▼──────────────┐
                                  │   │      scraping_jobs          │
                                  │   ├─────────────────────────────┤
                                  │   │ ● id          UUID (PK)     │
                                  │   │   source_id   UUID (FK) ────┘
                                  │   │   celery_task_id VARCHAR     │
                                  │   │   status      ENUM          │
                                  │   │   started_at  TIMESTAMP     │
                                  │   │   completed_at TIMESTAMP    │
                                  │   │   error_message TEXT        │
                                  │   │   leads_found INTEGER       │
                                  │   │   created_at  TIMESTAMP     │
                                  │   └─────────────────────────────┘
```

### Schema Definitions

#### users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4` | Unique user identifier |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, indexed | Login email |
| `hashed_password` | `VARCHAR(255)` | NOT NULL | bcrypt hash |
| `full_name` | `VARCHAR(255)` | NOT NULL | Display name |
| `is_active` | `BOOLEAN` | default `True` | Account enabled flag |
| `is_superuser` | `BOOLEAN` | default `False` | Admin privileges |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | default `now()`, on update `now()` | Last modified |

#### job_sources

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4` | Unique source identifier |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL, indexed | Owner |
| `name` | `VARCHAR(255)` | NOT NULL | Human-readable name |
| `platform` | `ENUM` | NOT NULL | `linkedin`, `naukri`, `upwork`, `indeed`, `custom` |
| `url` | `TEXT` | NOT NULL | Target URL to scrape |
| `scrape_config` | `JSONB` | default `{}` | Platform-specific settings, user preferences |
| `is_active` | `BOOLEAN` | default `True` | Source enabled flag |
| `schedule` | `ENUM` | NOT NULL, default `manual` | `hourly`, `daily`, `weekly`, `manual` |
| `last_scraped_at` | `TIMESTAMPTZ` | nullable | Last successful scrape |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | default `now()`, on update `now()` | Last modified |

#### leads

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4` | Unique lead identifier |
| `source_id` | `UUID` | FK → `job_sources.id` CASCADE, NOT NULL, indexed | Origin source |
| `platform` | `VARCHAR(50)` | NOT NULL | Platform the lead was scraped from |
| `title` | `VARCHAR(500)` | NOT NULL | Job title |
| `company` | `VARCHAR(255)` | NOT NULL | Company name |
| `location` | `VARCHAR(255)` | NOT NULL | Job location |
| `salary` | `VARCHAR(255)` | NOT NULL | Normalised salary string |
| `description` | `TEXT` | NOT NULL | Full job description |
| `requirements` | `TEXT` | NOT NULL | Key requirements |
| `contact_info` | `JSONB` | default `{}` | Extracted email/phone |
| `url` | `TEXT` | NOT NULL | Direct link to posting |
| `raw_data` | `JSONB` | default `{}` | Unmodified scrape output |
| `score` | `FLOAT` | NOT NULL, default `0.0` | AI relevance score (0–100) |
| `status` | `ENUM` | NOT NULL, default `new` | `new`, `contacted`, `interested`, `rejected`, `hired` |
| `embedding` | `VECTOR(1536)` | nullable | OpenAI text-embedding for semantic search |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Ingestion timestamp |
| `updated_at` | `TIMESTAMPTZ` | default `now()`, on update `now()` | Last modified |

#### scraping_jobs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4` | Unique job identifier |
| `source_id` | `UUID` | FK → `job_sources.id` CASCADE, NOT NULL, indexed | Associated source |
| `celery_task_id` | `VARCHAR(255)` | nullable | Celery task UUID |
| `status` | `ENUM` | NOT NULL, default `pending` | `pending`, `running`, `completed`, `failed` |
| `started_at` | `TIMESTAMPTZ` | nullable | Task start time |
| `completed_at` | `TIMESTAMPTZ` | nullable | Task end time |
| `error_message` | `TEXT` | nullable | Error details on failure |
| `leads_found` | `INTEGER` | NOT NULL, default `0` | Number of leads ingested |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Creation timestamp |

#### exports

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4` | Unique export identifier |
| `user_id` | `UUID` | FK → `users.id` CASCADE, NOT NULL, indexed | Owner |
| `format` | `ENUM` | NOT NULL | `csv`, `json` |
| `filters` | `JSONB` | default `{}` | Query filters used for export |
| `file_url` | `VARCHAR(500)` | NOT NULL | Path to generated file |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Creation timestamp |

---

## API Design

### Authentication Flow

The API uses **JWT Bearer Token** authentication. The flow is:

1. User sends credentials to `POST /api/v1/auth/login` (OAuth2 password form).
2. Backend validates credentials against `users.hashed_password` (bcrypt).
3. Backend returns `access_token` (60 min) and `refresh_token` (7 days).
4. Client includes `Authorization: Bearer <access_token>` in all subsequent requests.
5. `get_current_user` dependency extracts the token, decodes the JWT, and loads the
   `User` from the database.
6. If the token is expired, the client must re-authenticate.

### Resource Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|:------------:|
| `POST` | `/api/v1/auth/register` | Create a new user account | No |
| `POST` | `/api/v1/auth/login` | Obtain JWT access + refresh tokens | No |
| `GET` | `/api/v1/auth/me` | Get authenticated user profile | Yes |
| `GET` | `/api/v1/sources` | List all job sources for current user | Yes |
| `POST` | `/api/v1/sources` | Create a new job source | Yes |
| `GET` | `/api/v1/sources/{id}` | Get a single job source | Yes |
| `PUT` | `/api/v1/sources/{id}` | Update a job source | Yes |
| `DELETE` | `/api/v1/sources/{id}` | Delete a job source (cascade) | Yes |
| `GET` | `/api/v1/leads` | List leads with filters (status, score, platform, pagination) | Yes |
| `GET` | `/api/v1/leads/{id}` | Get a single lead with full details | Yes |
| `PATCH` | `/api/v1/leads/{id}` | Update lead (status, notes) | Yes |
| `DELETE` | `/api/v1/leads/{id}` | Delete a lead | Yes |
| `GET` | `/api/v1/jobs` | List all scraping jobs with status | Yes |
| `POST` | `/api/v1/jobs` | Trigger a scrape for a source (dispatches Celery task) | Yes |
| `GET` | `/api/v1/jobs/{id}` | Get scraping job status and results | Yes |
| `POST` | `/api/v1/exports` | Create a new export (CSV or JSON) | Yes |
| `GET` | `/api/v1/exports` | List all exports | Yes |
| `GET` | `/api/v1/exports/{id}/download` | Download an export file | Yes |
| `GET` | `/api/v1/dashboard/stats` | Get aggregated dashboard statistics | Yes |
| `GET` | `/health` | Liveness probe | No |
| `GET` | `/ready` | Readiness probe (DB + Redis) | No |

### Response Format

Successful single-resource response:

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Senior Python Developer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "salary": "150000-200000 USD",
  "description": "We are looking for a Senior Python Developer...",
  "requirements": "5+ years experience, FastAPI, PostgreSQL",
  "url": "https://linkedin.com/jobs/view/12345",
  "score": 87.5,
  "status": "new",
  "platform": "linkedin",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

Paginated list response:

```json
{
  "items": [
    { "id": "...", "title": "...", "score": 87.5 },
    { "id": "...", "title": "...", "score": 72.3 }
  ],
  "total": 150,
  "page": 1,
  "page_size": 25,
  "total_pages": 6
}
```

### Error Response Format

```json
{
  "detail": "Validation error",
  "errors": [
    { "field": "email", "message": "value is not a valid email address" },
    { "field": "password", "message": "String should have at least 8 characters" }
  ]
}
```

HTTP status codes used:

| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful GET, PUT, PATCH |
| `201` | Created | Successful POST (register, create source) |
| `202` | Accepted | Task dispatched (scrape triggered) |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Validation error, duplicate email |
| `401` | Unauthorized | Missing/invalid/expired JWT |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource does not exist |
| `422` | Unprocessable Entity | Pydantic validation failure |
| `500` | Internal Server Error | Unhandled exception |

---

## Security Architecture

### Authentication Flow

1. **Registration** — User submits email + password via `POST /auth/register`.
   Password is hashed with bcrypt (`passlib`) before storage. No plaintext passwords
   are ever persisted.

2. **Login** — User submits credentials via OAuth2 password flow (`POST /auth/login`).
   The server verifies the bcrypt hash and returns two JWTs:
   - `access_token` — short-lived (60 min), used for API requests
   - `refresh_token` — long-lived (7 days), used to obtain new access tokens

3. **Token Validation** — Every protected endpoint uses `get_current_user` dependency:
   - Extracts `Authorization: Bearer <token>` header
   - Decodes JWT with `python-jose` (HS256 algorithm)
   - Verifies `exp` claim (expiration)
   - Looks up `User` by `sub` (UUID) claim
   - Checks `is_active` flag

4. **Superuser Authorization** — `get_current_superuser` chains on top of
   `get_current_user` and additionally checks `is_superuser == True`.

### Security Measures

| Measure | Implementation | Detail |
|---------|---------------|--------|
| **Password Hashing** | bcrypt via `passlib` | 12-round salted hash; never stored in plaintext |
| **JWT Signing** | HMAC-SHA256 via `python-jose` | Secret key from `JWT_SECRET` env var (64+ chars) |
| **Token Expiration** | `exp` claim in JWT | Access: 60 min, Refresh: 7 days |
| **CORS** | FastAPI `CORSMiddleware` | Dev: `allow_origins=["*"]`; Prod: restricted to `FRONTEND_URL` |
| **SQL Injection** | Parameterised queries via SQLAlchemy | All queries use bound parameters; no raw SQL interpolation |
| **XSS** | React auto-escaping | JSX auto-escapes rendered content; no `dangerouslySetInnerHTML` |
| **CSRF** | JWT Bearer (token-based) | No cookies = no CSRF risk |
| **Rate Limiting** | Scraper rate limiter | Token-bucket algorithm in `scraper/utils/rate_limiter.py` |
| **Input Validation** | Pydantic v2 schemas | All API inputs validated and sanitised before processing |
| **Error Masking** | Production error handler | 500 errors return generic message; stack traces only in development |
| **Proxy Support** | HTTP/SOCKS5 rotation | `proxy_manager.py` rotates IPs to avoid scraping blacklists |
| **Environment Isolation** | `.env` files, `pydantic-settings` | Secrets never committed to version control |

---

## Deployment Architecture

### Docker Compose Services

| Service | Image | Container | Ports | Volumes | Health Check |
|---------|-------|-----------|-------|---------|-------------|
| **db** | `pgvector/pgvector:pg16` | `leadforge-db` | 5432 | `postgres_data`, `init.sql` | `pg_isready -U leadforge` |
| **redis** | `redis:7-alpine` | `leadforge-redis` | 6379 | `redis_data` | `redis-cli ping` |
| **backend** | Custom (Python) | `leadforge-backend` | 8000 | `backend/`, `scraper/`, `scraper_data` | Depends on db + redis healthy |
| **worker** | Custom (Python) | `leadforge-worker` | — | `backend/`, `scraper/`, `scraper_data` | Depends on db + redis healthy |
| **beat** | Custom (Python) | `leadforge-beat` | — | `backend/`, `scraper/` | Depends on redis |
| **frontend** | Custom (Node) | `leadforge-frontend` | 3000 | `frontend/src/`, `frontend/public/` | Depends on backend |

### Startup Order

```
db (healthy) ─────► backend (uvicorn + alembic upgrade)
redis (healthy) ──► worker (celery worker --concurrency=2)
                ──► beat (celery beat)
                   backend (running) ──► frontend (next start)
```

Docker Compose `depends_on` with `condition: service_healthy` ensures services
start in the correct order.

### Production Recommendations

| Aspect | Recommendation | Priority |
|--------|---------------|----------|
| **TLS/SSL** | Use Nginx or Caddy as reverse proxy with Let's Encrypt certificates | High |
| **JWT Secret** | Generate 64+ character random string; store in secrets manager | High |
| **Database Backups** | `pg_dump` cron job to S3/GCS; pg_basebackup for PITR | High |
| **Redis Persistence** | Enable AOF (`appendonly yes`) for durability | Medium |
| **Log Aggregation** | Centralise logs with Loki + Grafana or ELK stack | Medium |
| **Monitoring** | Prometheus exporters + Grafana dashboards for all services | Medium |
| **Secrets Management** | Use Docker secrets, HashiCorp Vault, or cloud KMS | High |
| **Container Resource Limits** | Set `mem_limit` and `cpus` in compose for each service | Medium |
| **Health Checks** | Configure load balancer health checks against `/health` and `/ready` | High |
| **Auto-restart** | `restart: unless-stopped` policy (already configured) | Low |
| **Database Connection Pooling** | PgBouncer between backend and PostgreSQL for high concurrency | Medium |
| **Worker Autoscaling** | Use `docker compose up --scale worker=N` or Kubernetes HPA | Low |

---

## Performance Considerations

### Database

| Technique | Implementation | Benefit |
|-----------|---------------|---------|
| **B-tree Indexes** | `users.email`, `job_sources.user_id`, `leads.source_id`, `scraping_jobs.source_id`, `exports.user_id` | Fast lookups on foreign keys and unique constraints |
| **pgvector Index** | `leads.embedding` column (VECTOR 1536) | Enables approximate nearest-neighbour search for semantic similarity |
| **Connection Pooling** | `pool_size=10`, `max_overflow=20` (async); `pool_size=5`, `max_overflow=10` (sync) | Reuses connections; avoids TCP handshake overhead |
| **Pre-ping** | `pool_pre_ping=True` on both engines | Detects stale connections before use |
| **JSONB Columns** | `scrape_config`, `contact_info`, `raw_data`, `filters` | Flexible semi-structured data without schema migrations |
| **CASCADE Deletes** | `ON DELETE CASCADE` on all foreign keys | Automatic cleanup of child records |

### Scraping

| Technique | Implementation | Benefit |
|-----------|---------------|---------|
| **Celery Concurrency** | `--concurrency=2` per worker (configurable) | Parallel task processing; balances CPU and memory |
| **Prefetch Multiplier** | `worker_prefetch_multiplier=1` | One task per worker at a time; prevents queue starvation |
| **Rate Limiter** | `scraper/utils/rate_limiter.py` — token bucket | Prevents overwhelming target sites |
| **Inter-request Delay** | `SCRAPER_DEFAULT_DELAY=2` (seconds) | Respects `robots.txt` norms |
| **Proxy Rotation** | `scraper/utils/proxy_manager.py` | Distributes requests across IPs to avoid blocking |
| **Retry with Back-off** | `max_retries=3`, `default_retry_delay=60` | Automatic retry on transient failures |
| **Timeout** | `SCRAPER_TIMEOUT=30` (seconds) | Prevents hung requests from blocking the queue |
| **Late Ack** | `task_acks_late=True` | Task is re-queued if worker crashes mid-execution |

### Frontend

| Technique | Implementation | Benefit |
|-----------|---------------|---------|
| **TanStack Query Caching** | `staleTime`, `gcTime` per query key | Avoids redundant API calls; serves cached data |
| **Background Refetch** | `refetchInterval: 30_000` on job status | Auto-updates scraping job progress |
| **Optimistic Updates** | `onMutate` in mutation hooks | Instant UI feedback before server confirms |
| **React.memo** | On expensive list components | Prevents unnecessary re-renders |
| **Virtual Scrolling** | (Planned) for lead tables > 1000 rows | Renders only visible rows; constant DOM size |
| **Code Splitting** | Next.js automatic route-based splitting | Each page loads its own JS bundle on navigation |
| **ISR** | `revalidate` on dashboard page | Server-side caching with periodic regeneration |
| **Image Optimisation** | `next/image` component | Automatic format conversion (WebP), lazy loading |

---

## Scaling Strategy

### Vertical Scaling (Bigger Machines)

| Component | Scaling Action | When to Apply |
|-----------|---------------|---------------|
| **PostgreSQL** | Increase RAM (for shared_buffers, work_mem); add CPU cores | Query latency > 200ms; cache hit ratio < 95% |
| **Redis** | Increase RAM (for in-memory datasets); faster CPU | Memory pressure > 80%; eviction occurring |
| **Backend** | Increase CPU cores; add RAM for connection pool | API latency > 500ms; p95 > 1s |
| **Worker** | Increase `--concurrency`; add RAM per worker (≈500 MB each) | Task queue depth > 100; scrape backlog growing |
| **Frontend** | More CPU for SSR; more RAM for build | Build time > 60s; SSR TTFB > 500ms |

### Horizontal Scaling (More Machines)

| Component | Scaling Method | Notes |
|-----------|---------------|-------|
| **Backend** | Multiple `backend` containers behind a load balancer | Stateless — no sticky sessions needed; JWT is self-contained |
| **Worker** | `docker compose up --scale worker=N` or Kubernetes HPA | Each worker pulls from the same Redis queue; linear scaling |
| **PostgreSQL** | Read replicas (primary + N replicas) | Use PgBouncer for connection management; replica lag monitoring |
| **Redis** | Redis Cluster (sharding) or Sentinel (HA) | Required when single-node memory > available RAM |
| **Frontend** | Multiple instances behind CDN / load balancer | Stateless; CDN serves static assets |

### Bottleneck Mitigation

| Bottleneck | Symptom | Mitigation |
|-----------|---------|-----------|
| **Database CPU** | High `pg_stat_activity`; slow queries | Add indexes; use `EXPLAIN ANALYZE`; consider read replicas |
| **Database Connections** | `FATAL: too many connections` | Increase `pool_size`; add PgBouncer; reduce `max_overflow` |
| **Worker Memory** | OOM kills; swap usage | Reduce `--concurrency`; set `mem_limit` in Docker |
| **Redis Memory** | Eviction events in log | Increase memory; configure `maxmemory-policy` (e.g., `allkeys-lru`) |
| **API Latency** | p95 > 1s | Add response caching in Redis; optimise N+1 queries |
| **Scrape Rate** | Tasks queuing > 5 min | Scale workers; reduce `delay`; add more proxies |
| **OpenAI API Rate** | 429 Too Many Requests | Batch scoring requests; implement exponential back-off; cache scores |
| **Disk I/O** | Slow export generation; high iowait | Use tmpfs for temporary files; stream exports instead of buffering |
| **Network Bandwidth** | Slow page loads; timeout on large responses | Enable gzip compression; paginate responses; use CDN |

### Scaling Decision Matrix

| Load Level | Users | Scrape Jobs/Day | Architecture |
|-----------|-------|----------------|-------------|
| **Development** | 1–5 | < 50 | Single Docker Compose stack (default) |
| **Small Production** | 5–50 | 50–500 | Same stack with 2–4 workers; Nginx TLS |
| **Medium Production** | 50–500 | 500–5,000 | Separate DB host; 4–8 workers; Redis Sentinel |
| **Large Production** | 500–5,000 | 5,000–50,000 | Kubernetes; DB read replicas; Redis Cluster; CDN |
| **Enterprise** | 5,000+ | 50,000+ | Multi-region; sharded DB; distributed scraping fleet |
