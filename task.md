# LeadForge Task Checklist

## Phase 1: End-to-End Testing & Verification
- `[ ]` Configure `.env` files with necessary credentials (LLM Provider, Resend).
- `[ ]` Verify Docker Compose stack runs correctly.
- `[ ]` Trigger real scraping tasks and verify ScrapeGraphAI extraction.
- `[ ]` Verify Next.js dashboard updates with real extracted data.

## Phase 2: Feature Enhancements
- `[ ]` **Resilient Scraper Engine**
  - `[ ]` Implement layered LLM fallback strategy in `scraper/engine.py`.
- `[ ]` **Semantic Search**
  - `[ ]` Map `embedding` column to pgvector types.
  - `[ ]` Add HNSW index to pgvector column.
  - `[ ]` Migrate to `text-embedding-3-small`.
  - `[ ]` Add cosine similarity search API endpoint.
- `[ ]` **Lead Deduplication**
  - `[ ]` Implement URL normalization (strip `utm_source` etc).
  - `[ ]` Generate SHA-256 hash for `lowercase(title + company + location)`.
  - `[ ]` Apply unique DB constraints for the hash to avoid parallel race conditions.
- `[ ]` **Email Notifications**
  - `[ ]` Implement `email_service.py` using Resend.
  - `[ ]` Modify `scrape_source_task` to generate a batched/digested email summary.
- `[ ]` **Automated Testing**
  - `[ ]` Setup `pytest` with `pytest-mock`/`respx` for backend.
  - `[ ]` Write strictly mocked API backend tests.
  - `[ ]` Setup Playwright for frontend E2E tests.
  - `[ ]` Configure Playwright network interception for backend mocking.

## Phase 3: Advanced Features & Scaling
- `[ ]` **Zero-Trust Multi-Tenancy**
  - `[ ]` Create Alembic migrations for PostgreSQL RLS policies.
  - `[ ]` Update backend connection/session contexts to pass tenant credentials to PG.
- `[ ]` **WebSocket Scaling Architecture**
  - `[ ]` Add Redis Pub/Sub integration.
  - `[ ]` Implement FastAPI WebSocket endpoints with Redis backplane.
- `[ ]` **Production Deployment Safeguards**
  - `[ ]` Add `mem_limit` configurations for Celery workers in Docker.
  - `[ ]` Prepare Caddy configuration for automatic Let's Encrypt TLS.
