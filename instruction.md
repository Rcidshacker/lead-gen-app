# LeadForge — Complete Instruction Manual

> **LeadForge** is an AI-powered lead generation and enrichment platform that automates
> job listing discovery, intelligent scoring, and contact extraction from multiple
> online job boards.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Architecture](#architecture)
7. [Scraper Engine Guide](#scraper-engine-guide)
8. [API Reference](#api-reference)
9. [Frontend Guide](#frontend-guide)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)

---

## Overview

LeadForge automates the entire lead-generation pipeline: it scrapes job listings from
LinkedIn, Naukri, UpWork, Indeed, and custom URLs, enriches each lead with an AI-powered
relevance score, stores everything in a PostgreSQL database with vector-search capability,
and presents the results through a modern React dashboard.

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 14 + React 18 + Tailwind CSS | User interface, dashboard, lead management |
| **Backend** | FastAPI 0.104 + Python 3.11 | REST API, authentication, business logic |
| **Database** | PostgreSQL 16 + pgvector | Persistent storage, vector embeddings |
| **Cache / Broker** | Redis 7 | Message broker for Celery, caching layer |
| **Task Queue** | Celery 5.3 | Async scraping jobs, lead scoring, exports |
| **Scraper Engine** | ScrapeGraphAI + Playwright | AI-driven web scraping with LLM extraction |
| **AI / LLM** | OpenAI GPT-4o-mini | Lead scoring, intelligent data extraction |
| **ORM** | SQLAlchemy 2.0 (async) | Database interaction with migration support |
| **Migrations** | Alembic | Schema versioning and migrations |

---

## Prerequisites

### Required

| Dependency | Minimum Version | Purpose |
|------------|----------------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend build toolchain |
| **Docker** | 20.10+ | Containerised deployment |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **OpenAI API Key** | — | ScrapeGraphAI extraction + lead scoring |

### Optional

| Dependency | Purpose |
|------------|---------|
| **Anthropic API Key** | Alternative LLM for scoring / extraction |
| **SMTP Server** | Email notifications for job completions |
| **Proxy Server (HTTP/SOCKS5)** | IP rotation for scraping at scale |

---

## Installation

### Option A: Docker Compose (Recommended)

This is the fastest path to a fully working environment. Docker Compose spins up all
six services (PostgreSQL, Redis, backend, Celery worker, Celery beat, and Next.js
frontend) in a single command.

#### Step 1 — Clone the repository

```bash
git clone <repository-url> lead-gen-app
cd lead-gen-app
```

#### Step 2 — Create environment files

```bash
# Backend .env
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql+asyncpg://leadforge:leadforge@db:5432/leadforge
DATABASE_SYNC_URL=postgresql+psycopg2://leadforge:leadforge@db:5432/leadforge
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
JWT_SECRET=change-me-to-a-random-64-char-string
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SGAI_MODEL=gpt-4o-mini
SGAI_TEMPERATURE=0.1
APP_ENV=development
LOG_LEVEL=INFO
EOF
```

> **Important:** Generate a secure `JWT_SECRET` — use `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

#### Step 3 — Build and start all services

```bash
docker compose build
docker compose up -d
```

#### Step 4 — Verify everything is running

```bash
docker compose ps          # all services should be "Up"
docker compose logs -f     # tail logs across all containers
```

Visit the health endpoint to confirm:

```bash
curl http://localhost:8000/health    # → {"status":"healthy","version":"0.1.0"}
curl http://localhost:8000/ready     # → {"status":"ready","checks":{"database":true,"redis":true}}
```

#### Step 5 — Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

### Option B: Manual Setup (Development)

Use this when you want to run each service individually for debugging or hot-reloading.

#### Step 1 — Start PostgreSQL and Redis

```bash
# Start only the database and cache containers
docker compose up -d db redis
```

#### Step 2 — Backend setup (Terminal 1)

```bash
cd backend

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env   # edit DATABASE_URL, JWT_SECRET, OPENAI_API_KEY

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 3 — Celery worker (Terminal 2)

```bash
cd backend
source .venv/bin/activate

celery -A app.workers.celery_app worker \
  --loglevel=info \
  --concurrency=2
```

#### Step 4 — Celery beat scheduler (Terminal 3)

```bash
cd backend
source .venv/bin/activate

celery -A app.workers.celery_app beat --loglevel=info
```

#### Step 5 — Frontend setup (Terminal 4)

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server (hot-reload)
npm run dev
```

The frontend will be available at http://localhost:3000 and will proxy API
requests to http://localhost:8000.

---

## Configuration

### Environment Variables

All configuration is centralised through environment variables (loaded from `.env`
files via `pydantic-settings`). The table below lists every variable:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_NAME` | `LeadForge` | No | Application name |
| `APP_ENV` | `development` | No | Environment: `development` or `production` |
| `APP_PORT` | `8000` | No | Backend listen port |
| `FRONTEND_URL` | `http://localhost:3000` | No | Frontend base URL (CORS) |
| `BACKEND_URL` | `http://localhost:8000` | No | Backend base URL (CORS) |
| `DATABASE_URL` | — | **Yes** | Async PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `DATABASE_SYNC_URL` | — | **Yes** | Sync PostgreSQL connection string (`postgresql+psycopg2://...`) |
| `REDIS_URL` | `redis://localhost:6379/0` | **Yes** | Redis connection URL |
| `CELERY_BROKER_URL` | — | **Yes** | Celery broker (typically same as `REDIS_URL`) |
| `CELERY_RESULT_BACKEND` | — | **Yes** | Celery result backend (typically same as `REDIS_URL`) |
| `JWT_SECRET` | — | **Yes** | Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | No | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | Access token lifetime in minutes |
| `OPENAI_API_KEY` | `""` | **Yes** | OpenAI API key for ScrapeGraphAI and lead scoring |
| `ANTHROPIC_API_KEY` | `""` | No | Anthropic API key (alternative LLM) |
| `SGAI_MODEL` | `gpt-4o-mini` | No | LLM model used by ScrapeGraphAI |
| `SGAI_TEMPERATURE` | `0.1` | No | Sampling temperature (lower = more deterministic) |
| `SGAI_MAX_TOKENS` | `4096` | No | Max tokens for LLM responses |
| `SCRAPER_DEFAULT_DELAY` | `2` | No | Delay (seconds) between scrape requests |
| `SCRAPER_MAX_CONCURRENT` | `3` | No | Maximum concurrent scrape operations |
| `SCRAPER_TIMEOUT` | `30` | No | HTTP request timeout in seconds |
| `LOG_LEVEL` | `INFO` | No | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `WEBHOOK_URLS` | `[]` | No | Comma-separated list of webhook URLs for notifications |
| `WEBHOOK_SECRET` | `""` | No | HMAC secret for webhook payload signing |

### ScrapeGraphAI Configuration

The scraper engine is configured through the `ScraperConfig` dataclass in
`scraper/engine.py`. You can override defaults via environment variables:

```python
@dataclass
class ScraperConfig:
    model: str = os.getenv("SGAI_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("SGAI_TEMPERATURE", "0.1"))
    headless: bool = True          # Browser runs headless (set False to debug)
    max_pages: int = 5             # Max pages to scrape per source
    delay: int = int(os.getenv("SCRAPER_DEFAULT_DELAY", "2"))
    timeout: int = int(os.getenv("SCRAPER_TIMEOUT", "30"))
    verbose: bool = True           # ScrapeGraphAI verbose logging
```

To pass additional options to ScrapeGraphAI (e.g., proxy, browser settings), modify
the `config` dict in the `ScraperEngine.scrape()` method:

```python
self._graph = SmartScraperGraph(
    prompt=prompt,
    source=url,
    config={
        "llm": {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        },
        "headless": self.config.headless,
        "verbose": self.config.verbose,
        # Optional proxy support
        # "proxy": {"server": "http://proxy:8080"},
    },
)
```

---

## Running the Application

### Development Mode

In development, all services use hot-reloading and verbose logging:

```bash
# Using Docker Compose
docker compose up

# Or manually (see Option B above — four terminals)
```

Key differences from production:
- CORS allows all origins (`allow_origins=["*"]`)
- SQLAlchemy echoes all SQL statements
- Uvicorn runs with `--reload`
- Celery worker runs with `--loglevel=info`

### Production Mode

```bash
# Build with production flags
docker compose up -d --build

# Or without Docker — use gunicorn for the backend
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Production considerations:
- Set `APP_ENV=production`
- Restrict CORS origins to `FRONTEND_URL`
- Use a reverse proxy (Nginx / Caddy) for TLS termination
- Set `headless=True` in scraper config
- Increase `CELERY_BROKER_URL` connection pool size

### Access URLs

| Service | Development | Production |
|---------|------------|------------|
| **Frontend** | http://localhost:3000 | https://your-domain.com |
| **Backend API** | http://localhost:8000 | https://your-domain.com/api |
| **Swagger UI** | http://localhost:8000/docs | Disabled in production |
| **ReDoc** | http://localhost:8000/redoc | Disabled in production |
| **pgAdmin** | — | http://localhost:5050 (optional) |
| **Flower (Celery Monitor)** | — | http://localhost:5555 (optional) |

---

## Architecture

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                     │
│                          http://localhost:3000                                │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │ HTTP / REST
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 14)                                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────────────┐  │
│  │ Dashboard │  │ Lead Manager │  │ Job Source │  │ Settings / Exports    │  │
│  └──────────┘  └──────────────┘  └───────────┘  └────────────────────────┘  │
│         TanStack Query (data fetching)  ·  Axios  ·  Recharts  ·  Tailwind    │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │ API calls (/api/v1/*)
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                     │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  Auth   │  │ Job Sources  │  │    Leads     │  │ Scraping Jobs API   │   │
│  │ Router  │  │   Router     │  │   Router     │  │      Router         │   │
│  └────┬────┘  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘   │
│       │              │                  │                     │              │
│  ┌────┴──────────────┴──────────────────┴─────────────────────┴──────────┐   │
│  │                     Services Layer                                    │   │
│  │   LeadScoringService  ·  ExportService  ·  WebhookService             │   │
│  └────┬──────────────────────┬────────────────────────┬──────────────────┘   │
└───────┼──────────────────────┼────────────────────────┼──────────────────────┘
        │                      │                        │
        ▼                      ▼                        ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────────────────────────────┐
│ PostgreSQL   │  │     Redis       │  │       Celery Worker                  │
│ + pgvector   │  │  (Broker/Cache) │  │  ┌────────────────────────────┐      │
│              │  │                 │  │  │  ScraperEngine              │      │
│  · users     │  │  · Task queue   │  │  │  ├─ LinkedInScraper         │      │
│  · leads     │  │  · Job results  │  │  │  ├─ NaukriScraper           │      │
│  · job_      │  │  · Rate limits  │  │  │  ├─ UpWorkScraper           │      │
│    sources   │  │                 │  │  │  ├─ IndeedScraper           │      │
│  · scraping  │  │                 │  │  │  └─ CustomScraper           │      │
│    _jobs     │  │                 │  │  └────────────┬───────────────┘      │
│  · exports   │  │                 │  │               │                       │
└──────────────┘  └─────────────────┘  │  ┌────────────▼───────────────┐      │
                                      │  │  ScrapeGraphAI              │      │
                                      │  │  (SmartScraperGraph)        │      │
                                      │  │  + OpenAI GPT-4o-mini       │      │
                                      │  └────────────┬───────────────┘      │
                                      └───────────────┼───────────────────────┘
                                                      │ HTTP / Playwright
                                                      ▼
                                      ┌──────────────────────────────────────┐
                                      │          Job Sites                   │
                                      │  LinkedIn · Naukri · UpWork          │
                                      │  Indeed · Custom URLs                │
                                      └──────────────────────────────────────┘
```

### Data Flow

The numbered steps below describe the complete lifecycle of a scraping job:

1. **User creates a Job Source** — The user navigates to "Sources" in the frontend,
   fills in a name, platform, URL, and optional schedule, and submits via `POST
   /api/v1/sources`.

2. **Backend persists the source** — FastAPI validates the payload via Pydantic,
   inserts a `JobSource` row into PostgreSQL, and returns the created record.

3. **User triggers a scrape** — The user clicks "Scrape Now" (or a scheduled Celery
   Beat trigger fires). The frontend calls `POST /api/v1/jobs` which dispatches a
   Celery task `scrape_source_task(source_id)`.

4. **Celery worker picks up the task** — The worker creates a `ScrapingJob` record
   with status `running` and passes the source to `ScraperEngine.scrape()`.

5. **ScraperEngine detects the platform** — It parses the URL hostname, looks up
   the platform in `SCRAPER_REGISTRY`, and selects the appropriate scraper class
   (e.g., `LinkedInScraper`).

6. **ScrapeGraphAI fetches and extracts** — The engine builds a `SmartScraperGraph`
   with a platform-specific prompt and the source URL. Playwright renders the page,
   the LLM extracts structured job data, and results are returned.

7. **Results are normalised** — Raw extraction output (which may vary in format) is
   normalised into a uniform schema: `title`, `company`, `location`, `salary`,
   `description`, `requirements`, `url`, `skills`, `platform`, `raw_data`.

8. **Leads are ingested and scored** — Each normalised listing is inserted as a
   `Lead` row. `LeadScoringService` calls OpenAI to compute a relevance score
   (0–100) based on the lead's match to the user's preferences.

9. **Frontend polls for updates** — TanStack Query refetches the scraping job
   status. When status changes to `completed`, the leads list refreshes and the
   dashboard stats update automatically.

### Directory Structure

```
lead-gen-app/
├── docker-compose.yml           # Multi-service orchestration (6 services)
├── README.md                    # Project overview
├── instruction.md               # This file
├── session.md                   # Development session log
│
├── backend/
│   ├── Dockerfile               # Backend + worker container image
│   ├── requirements.txt         # Python dependencies (26 packages)
│   ├── alembic.ini              # Alembic migration config
│   ├── init.sql                 # Initial DB setup (pgvector extension)
│   ├── .env                     # Environment variables (not committed)
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app, lifespan, middleware, error handlers
│       ├── config.py            # Pydantic Settings (all env vars)
│       ├── database.py          # Async + sync engines, session factories, Base
│       │
│       ├── models/              # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   ├── user.py          # User (id, email, hashed_password, full_name)
│       │   ├── lead.py          # Lead (id, title, company, score, embedding)
│       │   ├── job_source.py    # JobSource (id, platform, url, schedule)
│       │   ├── scraping_job.py  # ScrapingJob (id, status, celery_task_id)
│       │   └── export.py        # Export (id, format, filters, file_url)
│       │
│       ├── schemas/             # Pydantic v2 request/response schemas
│       │   ├── __init__.py
│       │   ├── user.py          # UserCreate, UserResponse, Token, TokenPayload
│       │   ├── lead.py          # LeadCreate, LeadUpdate, LeadResponse
│       │   ├── job_source.py    # JobSourceCreate, JobSourceResponse
│       │   ├── scraping_job.py  # ScrapingJobResponse
│       │   └── export.py        # ExportCreate, ExportResponse
│       │
│       ├── api/                 # FastAPI route handlers
│       │   ├── __init__.py
│       │   ├── router.py        # Root router — aggregates all sub-routers
│       │   ├── deps.py          # JWT auth, password hashing, get_current_user
│       │   ├── auth.py          # POST /auth/register, POST /auth/login, GET /auth/me
│       │   ├── leads.py         # CRUD endpoints for leads
│       │   ├── job_sources.py   # CRUD + scrape-trigger for job sources
│       │   ├── scraping_jobs.py # List + status for scraping jobs
│       │   ├── exports.py       # Create + download exports
│       │   └── dashboard.py     # Aggregated dashboard statistics
│       │
│       ├── services/            # Business logic layer
│       │   ├── __init__.py
│       │   ├── lead_scoring.py  # AI-powered lead relevance scoring
│       │   ├── export_service.py # CSV/JSON export generation
│       │   └── webhook_service.py # Outbound webhook notifications
│       │
│       └── workers/             # Celery tasks and configuration
│           ├── __init__.py
│           ├── celery_app.py    # Celery instance, config, beat schedule
│           └── tasks.py         # scrape_source_task, score_lead_task, generate_export_task
│
├── scraper/
│   ├── requirements.txt         # ScrapeGraphAI, Playwright, loguru
│   ├── __init__.py
│   ├── engine.py                # ScraperEngine — orchestrator + normaliser
│   │
│   ├── scrapers/                # Platform-specific scraper implementations
│   │   ├── __init__.py          # SCRAPER_REGISTRY mapping
│   │   ├── base.py              # BaseScraper ABC (parse_salary, clean_text)
│   │   ├── linkedin.py          # LinkedIn extraction prompt
│   │   ├── naukri.py            # Naukri extraction prompt
│   │   ├── upwork.py            # UpWork extraction prompt
│   │   └── indeed.py            # Indeed extraction prompt
│   │
│   ├── extractors/              # Post-processing extractors
│   │   ├── __init__.py
│   │   ├── job_extractor.py     # Job listing field extraction
│   │   └── contact_extractor.py # Email / phone extraction from descriptions
│   │
│   └── utils/                   # Shared scraping utilities
│       ├── __init__.py
│       ├── proxy_manager.py     # HTTP/SOCKS5 proxy rotation
│       └── rate_limiter.py      # Token-bucket rate limiter
│
├── frontend/
│   ├── Dockerfile               # Next.js container image
│   ├── package.json             # Node dependencies
│   ├── tsconfig.json            # TypeScript config
│   ├── next.config.js           # Next.js config (rewrites, env)
│   ├── tailwind.config.js       # Tailwind CSS theme
│   ├── postcss.config.js        # PostCSS plugins
│   │
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       │   ├── layout.tsx       # Root layout (providers, sidebar)
│       │   ├── page.tsx         # Home / redirect to dashboard
│       │   ├── globals.css      # Tailwind imports + custom styles
│       │   ├── providers.tsx    # TanStack QueryClientProvider
│       │   ├── login/page.tsx   # Login page
│       │   ├── dashboard/page.tsx  # Stats, charts, recent leads
│       │   ├── sources/page.tsx    # Job sources list
│       │   ├── sources/[id]/page.tsx # Single source detail
│       │   ├── leads/page.tsx       # Leads table with filters
│       │   ├── leads/[id]/page.tsx  # Lead detail
│       │   ├── jobs/page.tsx        # Scraping jobs history
│       │   └── settings/page.tsx    # User settings, API keys
│       │
│       ├── components/
│       │   ├── layout/          # AppShell, Sidebar, Header
│       │   ├── ui/              # Reusable UI primitives (Button, Card, Table, etc.)
│       │   ├── dashboard/       # StatsGrid, RecentLeads, ScrapeActivity, LeadSourceChart
│       │   ├── leads/           # LeadTable, LeadCard, LeadFilters, LeadScoreBadge
│       │   ├── sources/         # SourceCard, SourceForm
│       │   └── jobs/            # JobList, JobStatusBadge
│       │
│       ├── hooks/               # TanStack Query hooks
│       │   ├── useLeads.ts      # useLeads(), useLead(), useUpdateLead()
│       │   ├── useSources.ts    # useSources(), useCreateSource()
│       │   ├── useJobs.ts       # useJobs(), useCreateJob()
│       │   └── useDashboard.ts  # useDashboardStats()
│       │
│       ├── lib/                 # Client-side utilities
│       │   ├── api.ts           # Axios instance with JWT interceptor
│       │   ├── auth.ts          # Login, register, token storage
│       │   └── utils.ts         # cn(), formatDate(), formatSalary()
│       │
│       └── types/               # TypeScript interfaces
│           ├── lead.ts          # Lead, LeadFilters
│           ├── source.ts        # JobSource, PlatformType
│           ├── job.ts           # ScrapingJob, JobStatus
│           └── dashboard.ts     # DashboardStats
│
└── docs/
    └── architecture.md          # Detailed architecture document
```

---

## Scraper Engine Guide

### How It Works

The scraper engine follows a **Strategy Pattern** architecture:

1. `ScraperEngine` receives a source URL.
2. It calls `_detect_platform(url)` to identify the target site.
3. It looks up the matching scraper class in `SCRAPER_REGISTRY`.
4. The scraper provides a platform-specific extraction prompt.
5. `ScraperEngine` builds a `SmartScraperGraph` (from ScrapeGraphAI) with the
   prompt and URL.
6. Playwright renders the page, the LLM extracts structured data.
7. Raw results are normalised into a uniform job-listing schema via
   `_normalize_results()`.

### Supported Platforms

| Platform | Domain | Scraper Class | Special Fields |
|----------|--------|---------------|----------------|
| **LinkedIn** | `linkedin.com` | `LinkedInScraper` | posted_date, skills |
| **Naukri** | `naukri.com` | `NaukriScraper` | experience, education |
| **UpWork** | `upwork.com` | `UpWorkScraper` | job_type, experience_level |
| **Indeed** | `indeed.com` | `IndeedScraper` | rating, remote |
| **Custom** | Any URL | `BaseScraper` | (generic extraction) |

### Adding a New Source

To add a new platform (e.g., Glassdoor), create a scraper class and register it:

```python
# scraper/scrapers/glassdoor.py
from scraper.scrapers.base import BaseScraper


class GlassdoorScraper(BaseScraper):
    """Scraper for Glassdoor job listings."""

    platform: str = "glassdoor"

    def get_prompt(self) -> str:
        return (
            "Extract all job listings from this Glassdoor page. For each job, "
            "extract:\n"
            "- title: Job title\n"
            "- company: Company name\n"
            "- location: Job location\n"
            "- salary: Salary range if available\n"
            "- description: Full job description\n"
            "- requirements: Key requirements\n"
            "- url: Direct link to the job posting\n"
            "- rating: Company rating (1-5)\n"
            "- skills: List of required skills"
        )

    def get_search_config(self) -> dict:
        """Glassdoor-specific ScrapeGraphAI config overrides."""
        return {
            "wait_for": "[data-test='jobListing']",  # Wait for listings to load
        }
```

Then register it in `scraper/scrapers/__init__.py`:

```python
# scraper/scrapers/__init__.py
from scraper.scrapers.base import BaseScraper
from scraper.scrapers.glassdoor import GlassdoorScraper  # new
# ... other imports ...

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "upwork": UpWorkScraper,
    "indeed": IndeedScraper,
    "glassdoor": GlassdoorScraper,  # new
    "custom": BaseScraper,
}
```

Finally, add the domain to the detection map in `scraper/engine.py`:

```python
@staticmethod
def _detect_platform(url: str) -> str:
    host = urlparse(url).hostname or ""
    platform_map = {
        "linkedin.com": "linkedin",
        "naukri.com": "naukri",
        "upwork.com": "upwork",
        "indeed.com": "indeed",
        "glassdoor.com": "glassdoor",  # new
    }
    # ...
```

And update the `PlatformType` enum in `backend/app/models/job_source.py`:

```python
class PlatformType(str, enum.Enum):
    linkedin = "linkedin"
    naukri = "naukri"
    upwork = "upwork"
    indeed = "indeed"
    glassdoor = "glassdoor"   # new
    custom = "custom"
```

### ScrapeGraphAI Configuration Tips

- **Lower temperature** (`0.1`) produces more deterministic, structured extraction.
- **Headless mode** (`True`) is required for Docker deployments.
- **Verbose logging** helps debug extraction issues during development.
- For sites behind authentication, inject cookies via the `get_search_config()` method.
- Use the `delay` setting to avoid rate limiting on target sites.
- The `proxy_manager.py` utility can rotate proxies for high-volume scraping.

---

## API Reference

### Authentication

All protected endpoints require a JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

#### Register a new user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123", "full_name": "Jane Doe"}'
```

Response (`201 Created`):

```json
{
  "id": "a1b2c3d4-...",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepass123"
```

Response (`200 OK`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Key Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/register` | Register a new user | No |
| `POST` | `/api/v1/auth/login` | Obtain JWT tokens | No |
| `GET` | `/api/v1/auth/me` | Get current user profile | Yes |
| `GET` | `/api/v1/sources` | List all job sources | Yes |
| `POST` | `/api/v1/sources` | Create a new job source | Yes |
| `GET` | `/api/v1/sources/{id}` | Get a single source | Yes |
| `PUT` | `/api/v1/sources/{id}` | Update a source | Yes |
| `DELETE` | `/api/v1/sources/{id}` | Delete a source | Yes |
| `GET` | `/api/v1/leads` | List leads (with filters) | Yes |
| `GET` | `/api/v1/leads/{id}` | Get a single lead | Yes |
| `PATCH` | `/api/v1/leads/{id}` | Update lead status | Yes |
| `DELETE` | `/api/v1/leads/{id}` | Delete a lead | Yes |
| `GET` | `/api/v1/jobs` | List scraping jobs | Yes |
| `POST` | `/api/v1/jobs` | Trigger a scrape (creates Celery task) | Yes |
| `GET` | `/api/v1/jobs/{id}` | Get scraping job status | Yes |
| `POST` | `/api/v1/exports` | Create an export (CSV/JSON) | Yes |
| `GET` | `/api/v1/exports` | List exports | Yes |
| `GET` | `/api/v1/exports/{id}/download` | Download an export file | Yes |
| `GET` | `/api/v1/dashboard/stats` | Get dashboard statistics | Yes |
| `GET` | `/health` | Health check (liveness) | No |
| `GET` | `/ready` | Readiness check (DB + Redis) | No |

### Response Format

All API responses follow a consistent envelope. Successful responses return the
requested resource directly:

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Senior Python Developer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "salary": "150000-200000 USD",
  "score": 87.5,
  "status": "new",
  "platform": "linkedin",
  "created_at": "2025-01-15T10:30:00Z"
}
```

Paginated list responses include metadata:

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 25,
  "total_pages": 6
}
```

### Error Response Format

Errors return a consistent JSON envelope with `detail` and optional `errors`:

```json
// 401 Unauthorized
{
  "detail": "Could not validate credentials"
}

// 422 Validation Error
{
  "detail": "Validation error",
  "errors": [
    {"field": "email", "message": "value is not a valid email address"},
    {"field": "password", "message": "String should have at least 8 characters"}
  ]
}

// 404 Not Found
{
  "detail": "The requested resource was not found."
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

---

## Frontend Guide

### Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| **Next.js** | 14.2+ | React framework (App Router, SSR/ISR) |
| **React** | 18.3+ | UI library |
| **TypeScript** | 5.3+ | Type safety |
| **Tailwind CSS** | 3.4+ | Utility-first styling |
| **TanStack Query** | 5.17+ | Async state management, caching, refetching |
| **Axios** | 1.6+ | HTTP client with interceptors |
| **Recharts** | 2.10+ | Charts (bar, line, pie) |
| **Lucide React** | 0.303+ | Icon library |
| **date-fns** | 3.2+ | Date formatting |
| **clsx** + **tailwind-merge** | — | Conditional class composition (`cn()`) |

### Adding a New Page

To add a new page (e.g., `/analytics`), create the file and wire it into the layout:

```tsx
// frontend/src/app/analytics/page.tsx
"use client";

import { useDashboardStats } from "@/hooks/useDashboard";

export default function AnalyticsPage() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Leads</p>
          <p className="text-3xl font-semibold">{stats?.total_leads ?? 0}</p>
        </div>
      </div>
    </div>
  );
}
```

### Adding API Hooks

Create a new TanStack Query hook in `frontend/src/hooks/`:

```typescript
// frontend/src/hooks/useAnalytics.ts
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface AnalyticsData {
  leads_by_platform: Record<string, number>;
  avg_score: number;
  top_companies: { company: string; count: number }[];
}

export function useAnalytics() {
  return useQuery<AnalyticsData>({
    queryKey: ["analytics"],
    queryFn: async () => {
      const { data } = await api.get("/dashboard/analytics");
      return data;
    },
    staleTime: 5 * 60 * 1000, // cache for 5 minutes
    refetchInterval: 10 * 60 * 1000, // auto-refetch every 10 min
  });
}
```

Use the hook in any component:

```tsx
import { useAnalytics } from "@/hooks/useAnalytics";

function AnalyticsPanel() {
  const { data, error, isLoading } = useAnalytics();
  // ...
}
```

---

## Deployment

### Docker Compose (Recommended)

The provided `docker-compose.yml` defines six services:

```bash
# Production deployment
docker compose -f docker-compose.yml up -d --build

# View logs
docker compose logs -f backend worker

# Restart a single service
docker compose restart worker

# Stop everything
docker compose down

# Stop and remove volumes ( destructive — clears data )
docker compose down -v
```

### Scaling Workers

For high-volume scraping, increase the number of Celery workers:

```bash
# Scale to 4 workers
docker compose up -d --scale worker=4
```

Or configure Celery concurrency within each worker:

```bash
# Each worker handles 4 concurrent tasks
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

> **Note:** Monitor memory usage. Each worker loads Playwright (≈200 MB per instance).

### Reverse Proxy (Nginx)

For production, place Nginx in front of the frontend and backend:

```nginx
# /etc/nginx/sites-available/leadforge
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name leadforge.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name leadforge.example.com;

    ssl_certificate /etc/letsencrypt/live/leadforge.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/leadforge.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Larger body for bulk operations
        client_max_body_size 10M;
    }

    # Health checks (no auth required)
    location /health {
        proxy_pass http://backend;
    }

    location /ready {
        proxy_pass http://backend;
    }
}
```

Add Nginx to `docker-compose.yml`:

```yaml
nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./certs:/etc/letsencrypt
    depends_on:
      - backend
      - frontend
```

---

## Troubleshooting

### Database Connection Issues

**Symptom:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions:**

| Cause | Fix |
|-------|-----|
| DB container not ready | Wait for healthcheck: `docker compose up -d db && sleep 10` |
| Wrong credentials | Verify `DATABASE_URL` matches `POSTGRES_USER/PASSWORD` in compose |
| PostgreSQL not accepting connections | Check `docker compose logs db` for startup errors |
| `pgvector` extension missing | Ensure `init.sql` is mounted: `./backend/init.sql:/docker-entrypoint-initdb.d/init.sql` |

### Celery Worker Issues

**Symptom:** Tasks stuck in `pending` state, never picked up.

**Solutions:**

| Cause | Fix |
|-------|-----|
| Worker not running | `docker compose logs worker` — should show "celery@..." ready |
| Redis unreachable | `docker compose logs redis` — should show "Ready to accept connections" |
| Wrong broker URL | Ensure `CELERY_BROKER_URL` matches Redis container name in Docker |
| Import error | Check `docker compose logs worker` for Python traceback |

**Useful Celery commands:**

```bash
# Inspect active workers
docker compose exec worker celery -A app.workers.celery_app inspect active

# View registered tasks
docker compose exec worker celery -A app.workers.celery_app inspect registered

# Purge all pending tasks (destructive)
docker compose exec worker celery -A app.workers.celery_app purge

# Monitor with Flower (add to docker-compose.yml)
celery -A app.workers.celery_app flower --port=5555
```

### Scraping Issues

**Symptom:** Scraping job fails with `ScraperEngine` errors.

**Solutions:**

| Cause | Fix |
|-------|-----|
| `scrapegraphai` not installed | `pip install scrapegraphai` or check `scraper/requirements.txt` |
| OpenAI API key missing | Set `OPENAI_API_KEY` in `.env` |
| Rate limited by target site | Increase `SCRAPER_DEFAULT_DELAY` (e.g., `5`) |
| Page requires authentication | Inject cookies via `get_search_config()` in the scraper |
| Timeout during extraction | Increase `SCRAPER_TIMEOUT` (e.g., `60`) |
| Headless browser fails in Docker | Ensure Playwright browsers are installed in the Dockerfile |

### Playwright / Browser Issues

**Symptom:** `BrowserType.launch` fails or pages don't render.

**Solutions:**

```bash
# Install Playwright browsers (run inside the backend container)
docker compose exec backend npx playwright install --with-deps chromium

# Or add to the backend Dockerfile
RUN npx playwright install --with-deps chromium
```

| Cause | Fix |
|-------|-----|
| Missing browser binaries | `playwright install --with-deps chromium` |
| Out of memory | Increase Docker memory limit (4 GB minimum) |
| JavaScript rendering timeout | Increase `SCRAPER_TIMEOUT` in `.env` |
| Missing system dependencies | Install `libatk1.0-0`, `libgbm1`, etc. in Dockerfile |

### General Debugging Tips

```bash
# Full backend logs (SQL + application)
docker compose logs -f backend | head -100

# Check database connectivity
docker compose exec db psql -U leadforge -d leadforge -c "SELECT 1;"

# Check Redis connectivity
docker compose exec redis redis-cli ping

# Run a single Celery task manually
docker compose exec backend python -c "
from app.workers.tasks import scrape_source_task
result = scrape_source_task('source-uuid-here')
print(result)
"

# Check OpenAI API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models | head -20
```
