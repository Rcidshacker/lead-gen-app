# LeadForge Implementation Plan

## Goal Description
LeadForge is currently a fully functional MVP for an AI-powered lead generation and enrichment platform. It scrapes job listings from various platforms, scores them, and presents them in a Next.js dashboard. The goal of this plan is to outline the next steps to transition the project from an MVP to a robust, highly-scalable, production-ready application.

## User Review Required
Please review the comprehensively updated plan featuring expert suggestions for all phases. No implementation will begin until you give the final approval.

## Proposed Changes

### Phase 1: End-to-End Testing & Verification (Immediate)
*Execution paused pending user confirmation.*
Before adding new features, we must ensure the existing MVP works flawlessly with real data.
- **Environment Configuration**: Setup `.env` files with valid credentials. This includes support for **any LLM API provider** (OpenAI, OpenRouter, Gemini, Grok, Claude, Nvidia, etc.) and your Resend API key.
- Run the full Docker Compose stack.
- Create job sources using real URLs (LinkedIn, Naukri, Indeed) and trigger Celery scraping tasks.
- Verify that ScrapeGraphAI extracts the data correctly and the Next.js dashboard updates accordingly.

---

### Phase 2: Feature Enhancements (Short-Term)

#### 1. Resilient Scraper Engine
- **[MODIFY] `scraper/engine.py`**: Implement a layered fallback strategy for LLM extraction to ensure agentic web scraping workflows remain resilient even when the primary model hallucinates or times out.

#### 2. Semantic Search with pgvector
Implement similarity search to allow users to find leads related to a specific query.
- **[MODIFY] `backend/app/models/lead.py`**: Configure the `embedding` column and implement an **HNSW (Hierarchical Navigable Small World)** index rather than an exact k-NN index to dramatically improve query speeds at scale.
- **[MODIFY] `backend/app/services/lead_scoring.py`**: Migrate to **`text-embedding-3-small`** to generate embeddings, which is approximately 5x cheaper and yields higher accuracy (MTEB) scores.
- **[MODIFY] `backend/app/api/leads.py`**: Add a search endpoint performing cosine similarity search via pgvector.

#### 3. Lead Deduplication
Prevent identical job listings from cluttering the database across multiple scrape runs using a high-performance hybrid approach.
- **[MODIFY] Scraper Normalizer**: Implement URL normalization (stripping tracking parameters like `utm_source`).
- **[MODIFY] `backend/app/services/lead_scoring.py`**: Generate a deterministic SHA-256 hash of `lowercase(title + company + location)` upon ingestion.
- **[MODIFY] `backend/app/models/lead.py` & Database**: Set database-level unique constraints on this hash to prevent race conditions during parallel Celery scraping tasks.

#### 4. Email Notifications (via Resend)
Notify users via an intelligent email batching system to prevent rate limits and spam.
- **[NEW] `backend/app/services/email_service.py`**: Create a new service using the Resend Python SDK.
- **[MODIFY] `backend/app/workers/tasks.py`**: Instead of individual alerts, trigger a single **"Digest" email** summarizing the scrape job (e.g., "Scrape complete: 45 new leads found, 3 high-priority").

#### 5. Automated Testing Suite
Ensure reliability and prevent regressions using strict mocking.
- **[NEW] `backend/tests/`**: Add `pytest` configuration. Use libraries like `pytest-mock` or `respx` to strictly mock LLM APIs and ScrapeGraphAI calls, preventing the CI/CD pipeline from burning API credits.
- **[NEW] `frontend/tests/`**: Setup **Playwright** for E2E testing. Utilize Playwright's network interception to mock the FastAPI backend, ensuring UI tests are deterministic and decoupled from a populated database.

---

### Phase 3: Advanced Features & Scaling (Medium-Term)

#### 1. Zero-Trust Multi-Tenancy
- **[MODIFY] `backend/app/database.py` & Migrations**: Implement **PostgreSQL Row-Level Security (RLS)** policies directly on the tables. This acts as a database-level firewall to prevent cross-tenant data leaks, moving beyond simple application-layer filtering.

#### 2. WebSocket Scaling Architecture
- **[MODIFY] `backend/app/api/jobs.py` & Infrastructure**: Replace polling with real-time WebSocket connections. Integrate a **Redis Pub/Sub backplane** to broadcast progress messages reliably across all Uvicorn/Gunicorn worker processes.

#### 3. Production Deployment Safeguards
- **[MODIFY] `docker-compose.yml` & Infra configs**:
  - Set strict memory limits (`mem_limit`) for Celery workers to safeguard against Playwright-induced Out-Of-Memory (OOM) crashes during heavy concurrent scrapes.
  - Swap Nginx for **Caddy** on the VPS. Caddy handles automatic Let's Encrypt TLS certificate provisioning natively, reducing configuration overhead.

## Verification Plan

### Automated Tests
- Run backend test suite: `docker compose exec backend pytest` (with 100% mocked external API calls).
- Run frontend E2E suite: `npx playwright test` (with network interception mocking the backend).

### Manual Verification
- Perform a manual UI walkthrough of the HNSW semantic search.
- Verify the digested email format using the Resend sandbox.
- Trigger parallel scrape runs on the same URL to verify the SHA-256 unique constraints block duplicates without race conditions.
