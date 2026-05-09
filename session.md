# LeadForge — Development Session Log

---

## Session 001

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Status** | MVP Complete |
| **Goal** | Build a fully functional AI-powered lead generation platform from scratch |
| **Duration** | Single development session |
| **Phase** | Phases 1–8 (complete) |

---

## Context & Motivation

### What We're Building

**LeadForge** is an AI-powered lead generation and enrichment platform that automates
the discovery of job listings from multiple online job boards. The system scrapes
job postings from platforms like LinkedIn, Naukri, UpWork, and Indeed, enriches each
lead with an AI-powered relevance score (0–100), stores structured data with vector
embeddings for semantic search, and exposes the results through a modern dashboard
with export capabilities.

### Why

Recruitment agencies, sales teams, and business development professionals spend
significant time manually browsing job boards to identify potential leads. LeadForge
automates this entire pipeline — from discovery to scoring — enabling users to
focus on high-value outreach rather than repetitive data collection.

**Key value propositions:**

- **Multi-platform scraping** — One source configuration covers LinkedIn, Naukri,
  UpWork, Indeed, and any custom URL.
- **AI-powered extraction** — ScrapeGraphAI + GPT-4o-mini produce structured data
  from unstructured HTML, handling site-specific layouts automatically.
- **Intelligent scoring** — Each lead receives a relevance score based on the user's
  preferences, allowing rapid prioritisation.
- **Async processing** — Long-running scrape jobs are handled by Celery workers,
  keeping the API responsive.
- **Export-ready** — CSV and JSON export with configurable filters.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend Framework** | Next.js 14 (App Router) | Server components, file-based routing, built-in SSR/ISR, excellent DX with TypeScript. Most popular React meta-framework with strong ecosystem. |
| **Backend Framework** | FastAPI 0.104 | Async-first, automatic OpenAPI docs, Pydantic validation, dependency injection. 3–5x faster than Flask/Django for JSON APIs. |
| **Scraper Engine** | ScrapeGraphAI + Playwright | LLM-driven extraction adapts to any page layout without fragile CSS selectors. Playwright handles JavaScript-rendered content. |
| **Task Queue** | Celery 5.3 + Redis | Mature, battle-tested distributed task queue. Redis doubles as cache and message broker. Celery Beat for scheduled scraping. |
| **Database** | PostgreSQL 16 + pgvector | Relational integrity for structured data + pgvector extension for 1536-dimensional embeddings (OpenAI `text-embedding-ada-002`). |
| **ORM** | SQLAlchemy 2.0 (async) | Unified async/sync engines (FastAPI + Celery). Mapped column syntax, type-safe queries, Alembic migrations. |
| **Styling** | Tailwind CSS 3.4 | Utility-first approach with zero runtime cost. Consistent design system via `tailwind.config.js`. |
| **Data Fetching** | TanStack Query 5 | Server state management with automatic caching, refetching, and stale-while-revalidate. |
| **AI / LLM** | OpenAI GPT-4o-mini | Best cost/performance ratio for extraction and scoring. `temperature=0.1` for deterministic structured output. |
| **Authentication** | JWT (python-jose + passlib) | Stateless auth suitable for SPA + API. Bcrypt password hashing. OAuth2 password flow compatible with Swagger UI. |
| **Charts** | Recharts 2.10 | Composable, React-native charting library. Supports bar, line, pie, and area charts. |
| **Icons** | Lucide React | Lightweight, consistent icon set with tree-shaking. |

---

## MVP Scope

### In Scope

- [x] User registration and login (JWT authentication)
- [x] Job source CRUD (create, read, update, delete)
- [x] Multi-platform scraping (LinkedIn, Naukri, UpWork, Indeed, Custom)
- [x] ScrapeGraphAI integration with LLM extraction
- [x] Async scraping via Celery workers
- [x] Lead ingestion with AI-powered relevance scoring
- [x] Lead listing with filters (status, score, platform)
- [x] Lead detail view
- [x] Scraping job history and status tracking
- [x] Dashboard with aggregated statistics
- [x] CSV and JSON export generation
- [x] Celery Beat scheduled task (export cleanup)
- [x] Webhook notifications
- [x] Docker Compose deployment (6 services)
- [x] Environment-based configuration (Pydantic Settings)
- [x] Database migrations with Alembic
- [x] Health and readiness endpoints
- [x] Global error handlers
- [x] CORS middleware (dev / prod modes)

### Out of Scope (Future Phases)

- [ ] Multi-tenancy / team-based access control
- [ ] Email notification system (SMTP integration)
- [ ] Semantic search via pgvector embeddings
- [ ] Lead deduplication (fuzzy matching)
- [ ] OAuth2 social login (Google, GitHub)
- [ ] Rate limiting middleware (per-user)
- [ ] Automated browser fingerprint rotation
- [ ] Scraping proxy rotation at scale
- [ ] Real-time WebSocket updates for job progress
- [ ] Mobile-responsive design optimisation
- [ ] CSV bulk import of job sources
- [ ] Zapier / Make.com integrations
- [ ] Audit logging for compliance
- [ ] End-to-end test suite (Cypress / Playwright)
- [ ] CI/CD pipeline (GitHub Actions)

---

## Files Created

### Root (2 files)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 6-service orchestration (db, redis, backend, worker, beat, frontend) |
| `README.md` | Project overview and quick-start guide |

### Backend (23 files)

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.11 slim + Playwright deps |
| `requirements.txt` | 26 Python packages |
| `alembic.ini` | Alembic migration config |
| `init.sql` | pgvector extension init |
| `app/__init__.py` | Package marker |
| `app/main.py` | FastAPI app, lifespan, CORS, error handlers |
| `app/config.py` | Pydantic Settings (all env vars) |
| `app/database.py` | Async + sync engines, session factories, Base class |
| `app/models/__init__.py` | Model re-exports |
| `app/models/user.py` | User ORM model |
| `app/models/lead.py` | Lead ORM model (pgvector embedding) |
| `app/models/job_source.py` | JobSource ORM model (platform, schedule enums) |
| `app/models/scraping_job.py` | ScrapingJob ORM model (status enum) |
| `app/models/export.py` | Export ORM model (format enum) |
| `app/schemas/__init__.py` | Schema re-exports |
| `app/schemas/user.py` | UserCreate, UserResponse, Token, TokenPayload |
| `app/schemas/lead.py` | LeadCreate, LeadUpdate, LeadResponse |
| `app/schemas/job_source.py` | JobSourceCreate, JobSourceResponse |
| `app/schemas/scraping_job.py` | ScrapingJobResponse |
| `app/schemas/export.py` | ExportCreate, ExportResponse |
| `app/api/router.py` | Root API router aggregation |
| `app/api/deps.py` | JWT auth, password hashing, get_current_user |
| `app/api/auth.py` | Register, login, /me endpoints |
| `app/api/leads.py` | Lead CRUD endpoints |
| `app/api/job_sources.py` | JobSource CRUD + scrape trigger |
| `app/api/scraping_jobs.py` | Scraping job list + status |
| `app/api/exports.py` | Export creation + download |
| `app/api/dashboard.py` | Dashboard stats aggregation |
| `app/services/__init__.py` | Service re-exports |
| `app/services/lead_scoring.py` | AI lead relevance scoring |
| `app/services/export_service.py` | CSV/JSON file generation |
| `app/services/webhook_service.py` | Outbound webhook notifications |
| `app/workers/__init__.py` | Workers package marker |
| `app/workers/celery_app.py` | Celery config, beat schedule |
| `app/workers/tasks.py` | 4 Celery tasks (scrape, score, export, cleanup) |

**Total: 23 files**

### Scraper (12 files)

| File | Purpose |
|------|---------|
| `scraper/__init__.py` | Package marker |
| `scraper/requirements.txt` | ScrapeGraphAI, Playwright, loguru |
| `scraper/engine.py` | ScraperEngine orchestrator + normaliser |
| `scraper/scrapers/__init__.py` | SCRAPER_REGISTRY (platform → class map) |
| `scraper/scrapers/base.py` | BaseScraper ABC (parse_salary, clean_text) |
| `scraper/scrapers/linkedin.py` | LinkedIn-specific prompt |
| `scraper/scrapers/naukri.py` | Naukri-specific prompt |
| `scraper/scrapers/upwork.py` | UpWork-specific prompt |
| `scraper/scrapers/indeed.py` | Indeed-specific prompt |
| `scraper/extractors/__init__.py` | Extractors package |
| `scraper/extractors/job_extractor.py` | Job field extraction |
| `scraper/extractors/contact_extractor.py` | Email/phone extraction |
| `scraper/utils/__init__.py` | Utils package |
| `scraper/utils/proxy_manager.py` | HTTP/SOCKS5 proxy rotation |
| `scraper/utils/rate_limiter.py` | Token-bucket rate limiter |

**Total: 12 files**

### Frontend (33 files)

| File | Purpose |
|------|---------|
| `Dockerfile` | Node 18 + Next.js build |
| `package.json` | Dependencies (Next.js, React, TanStack Query, etc.) |
| `tsconfig.json` | TypeScript configuration |
| `next.config.js` | Next.js config (API rewrites, env) |
| `tailwind.config.js` | Tailwind theme |
| `postcss.config.js` | PostCSS plugins |
| `src/app/layout.tsx` | Root layout (providers, sidebar) |
| `src/app/page.tsx` | Home page |
| `src/app/globals.css` | Tailwind imports |
| `src/app/providers.tsx` | QueryClientProvider |
| `src/app/login/page.tsx` | Login page |
| `src/app/dashboard/page.tsx` | Dashboard (stats, charts) |
| `src/app/sources/page.tsx` | Sources list |
| `src/app/sources/[id]/page.tsx` | Source detail |
| `src/app/leads/page.tsx` | Leads table with filters |
| `src/app/leads/[id]/page.tsx` | Lead detail |
| `src/app/jobs/page.tsx` | Scraping jobs history |
| `src/app/settings/page.tsx` | Settings page |
| `src/components/layout/AppShell.tsx` | App shell wrapper |
| `src/components/layout/Sidebar.tsx` | Navigation sidebar |
| `src/components/layout/Header.tsx` | Top header bar |
| `src/components/ui/Button.tsx` | Button component |
| `src/components/ui/Card.tsx` | Card component |
| `src/components/ui/Input.tsx` | Input component |
| `src/components/ui/Table.tsx` | Table component |
| `src/components/ui/Select.tsx` | Select component |
| `src/components/ui/Badge.tsx` | Badge component |
| `src/components/ui/Modal.tsx` | Modal component |
| `src/components/dashboard/StatsGrid.tsx` | Stats cards |
| `src/components/dashboard/RecentLeads.tsx` | Recent leads list |
| `src/components/dashboard/ScrapeActivity.tsx` | Scrape activity feed |
| `src/components/dashboard/LeadSourceChart.tsx` | Pie/bar chart |
| `src/components/leads/LeadTable.tsx` | Leads data table |
| `src/components/leads/LeadCard.tsx` | Lead card view |
| `src/components/leads/LeadFilters.tsx` | Filter controls |
| `src/components/leads/LeadScoreBadge.tsx` | Score indicator |
| `src/components/sources/SourceCard.tsx` | Source card |
| `src/components/sources/SourceForm.tsx` | Source create/edit form |
| `src/components/jobs/JobList.tsx` | Job history list |
| `src/components/jobs/JobStatusBadge.tsx` | Job status indicator |
| `src/hooks/useLeads.ts` | Lead CRUD hooks |
| `src/hooks/useSources.ts` | Source CRUD hooks |
| `src/hooks/useJobs.ts` | Job hooks |
| `src/hooks/useDashboard.ts` | Dashboard stats hook |
| `src/lib/api.ts` | Axios instance with JWT interceptor |
| `src/lib/auth.ts` | Auth utilities |
| `src/lib/utils.ts` | cn(), formatDate(), formatSalary() |
| `src/types/lead.ts` | Lead TypeScript interfaces |
| `src/types/source.ts` | Source TypeScript interfaces |
| `src/types/job.ts` | Job TypeScript interfaces |
| `src/types/dashboard.ts` | Dashboard TypeScript interfaces |

**Total: 33 files**

### Documentation (3 files)

| File | Purpose |
|------|---------|
| `instruction.md` | Complete instruction manual |
| `session.md` | This file — development session log |
| `docs/architecture.md` | Detailed architecture document |

**Total: 3 files**

### Grand Total

| Section | Files |
|---------|-------|
| Root | 2 |
| Backend | 23 |
| Scraper | 12 |
| Frontend | 33 |
| Documentation | 3 |
| **Total** | **73** |

---

## Key Design Patterns

### 1. Repository Pattern (Implicit)

SQLAlchemy models serve as the data access layer. Each model encapsulates table
schema, relationships, and constraints. The services layer operates on ORM objects
rather than raw SQL, keeping queries close to the data they represent.

### 2. Service Layer

Business logic is extracted into service classes, keeping API route handlers thin:

- `LeadScoringService` — Encapsulates OpenAI API calls for lead scoring.
- `ExportService` — Handles CSV/JSON file generation and cleanup.
- `WebhookService` — Manages outbound HTTP notifications.

```python
# Example: thin route handler delegates to service
@router.post("/sources/{id}/scrape")
async def trigger_scrape(source_id: uuid.UUID, ...):
    job = scraping_service.create_job(source_id)
    scrape_source_task.delay(str(source_id))
    return job
```

### 3. Dependency Injection

FastAPI's `Depends()` mechanism is used throughout:

- `get_db()` — Injects async database sessions with auto-commit/rollback.
- `get_current_user()` — Extracts and validates JWT, injects `User` object.
- `get_current_superuser()` — Same, with admin check.

```python
async def read_leads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ...
```

### 4. Task Queue Pattern

Long-running operations (scraping, scoring, export) are delegated to Celery workers.
The API returns immediately with a job reference, and the frontend polls for status.

```python
# API dispatches task, returns job ID
task = scrape_source_task.delay(str(source_id))

# Frontend polls
GET /api/v1/jobs/{job_id}  →  {"status": "running", "leads_found": 0}
GET /api/v1/jobs/{job_id}  →  {"status": "completed", "leads_found": 42}
```

### 5. Strategy Pattern

Platform-specific scraping logic is encapsulated in separate scraper classes behind
a common `BaseScraper` interface. The `SCRAPER_REGISTRY` maps platform names to
scraper classes, enabling runtime selection:

```python
SCRAPER_REGISTRY = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "upwork": UpWorkScraper,
    "indeed": IndeedScraper,
    "custom": BaseScraper,
}
```

### 6. Pydantic Schemas (Validation Layer)

Every API endpoint uses typed Pydantic v2 schemas for request/response validation.
This ensures type safety, automatic documentation, and clean error messages:

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
```

---

## Data Model Summary

| Model | Table | Key Columns | Relationships |
|-------|-------|-------------|---------------|
| **User** | `users` | `id`, `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser` | One → Many JobSources, One → Many Exports |
| **JobSource** | `job_sources` | `id`, `user_id`, `name`, `platform`, `url`, `scrape_config`, `schedule` | Many → One User, One → Many Leads, One → Many ScrapingJobs |
| **Lead** | `leads` | `id`, `source_id`, `platform`, `title`, `company`, `score`, `embedding`, `status` | Many → One JobSource |
| **ScrapingJob** | `scraping_jobs` | `id`, `source_id`, `celery_task_id`, `status`, `leads_found`, `error_message` | Many → One JobSource |
| **Export** | `exports` | `id`, `user_id`, `format`, `filters`, `file_url` | Many → One User |

---

## API Design

| Resource | Endpoints | Methods |
|----------|-----------|---------|
| **Auth** | `/auth/register`, `/auth/login`, `/auth/me` | POST, POST, GET |
| **Job Sources** | `/sources`, `/sources/{id}` | GET, POST, PUT, DELETE |
| **Leads** | `/leads`, `/leads/{id}` | GET, PATCH, DELETE |
| **Scraping Jobs** | `/jobs`, `/jobs/{id}` | GET, POST |
| **Exports** | `/exports`, `/exports/{id}/download` | GET, POST |
| **Dashboard** | `/dashboard/stats` | GET |
| **System** | `/health`, `/ready` | GET, GET |

All resource endpoints are under the `/api/v1` prefix. Authentication endpoints
are public; all others require a JWT bearer token.

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project scaffolding — Docker Compose, directory structure, env config | Completed |
| **Phase 2** | Database models — User, Lead, JobSource, ScrapingJob, Export with SQLAlchemy | Completed |
| **Phase 3** | Pydantic schemas — Request/response validation for all models | Completed |
| **Phase 4** | API routes — Auth (register/login), CRUD for all resources, dashboard stats | Completed |
| **Phase 5** | Scraper engine — ScraperEngine, BaseScraper, 4 platform scrapers, ScrapeGraphAI integration | Completed |
| **Phase 6** | Celery workers — scrape_source_task, score_lead_task, generate_export_task, cleanup task, beat scheduler | Completed |
| **Phase 7** | Frontend — Next.js pages, React components, TanStack Query hooks, Axios API client, Tailwind styling | Completed |
| **Phase 8** | Documentation — instruction.md, session.md, docs/architecture.md | Completed |

---

## Next Steps

### Immediate (Before First Real Use)

1. **Test the full stack** — Run the Docker Compose stack end-to-end, register a user,
   create a job source, trigger a scrape, verify leads appear in the dashboard.

2. **Use real URLs** — Test with actual LinkedIn/Naukri/Indeed search result URLs.
   Verify ScrapeGraphAI extracts structured data correctly.

3. **Configure a valid OpenAI API key** — Required for both scraping (ScrapeGraphAI)
   and lead scoring. Verify the key has sufficient credits.

### Short-Term Improvements

4. **Add pgvector semantic search** — Generate embeddings for lead descriptions
   using OpenAI `text-embedding-ada-002` and enable similarity search.

5. **Implement lead deduplication** — Fuzzy matching on title + company to avoid
   duplicate entries across scraping runs.

6. **Add email notifications** — Integrate SMTP to notify users when scraping jobs
   complete or high-score leads are discovered.

7. **Write tests** — Unit tests for services, integration tests for API endpoints,
   and E2E tests with Playwright for the frontend.

### Medium-Term

8. **Deploy to production** — Set up a VPS or cloud instance, configure Nginx with
   TLS, set up monitoring (Prometheus + Grafana).

9. **Add WebSocket updates** — Push real-time scraping progress to the frontend
   instead of polling.

10. **Multi-tenancy** — Add team-based access control with role-based permissions.
