"""Celery task definitions for LeadForge background processing.

Tasks defined here:
- ``scrape_source_task``   – Full scrape pipeline for a job source.
- ``score_lead_task``       – (Re-)score a single lead via AI.
- ``generate_export_task``  – Build a CSV/JSON export file.
- ``cleanup_old_exports_task`` – Periodic removal of stale export files.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SyncSessionLocal
from app.models.lead import Lead, LeadStatus
from app.models.job_source import JobSource
from app.models.scraping_job import ScrapingJob, JobStatus
from app.models.export import Export
from app.services.lead_scoring import LeadScoringService
from app.services.export_service import ExportService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: run an async coroutine from a synchronous Celery task
# ---------------------------------------------------------------------------
def _run_async(coro):
    """Execute an async coroutine in a new event loop.

    Celery workers are synchronous by default, so any ``async`` service call
    must be wrapped with this helper.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Task 1 – Scrape a job source end-to-end
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.tasks.scrape_source_task",
)
def scrape_source_task(self, source_id: str, job_id: str | None = None) -> dict:
    """Execute the full scrape → ingest → score pipeline for *source_id*.

    Steps
    -----
    1. Look up the ``JobSource`` and resolve or create a ``ScrapingJob`` record.
    2. Use the ``ScraperEngine`` to fetch listings from the source URL.
    3. Upsert scraped items as ``Lead`` rows in the DB.
    4. Score each new lead via ``LeadScoringService``.
    5. Mark the scraping job as completed (or failed on error).

    Returns
    -------
    dict
        ``{"status": "completed", "leads_found": <int>}`` on success.
    """
    source_uuid = uuid.UUID(source_id)

    with SyncSessionLocal() as db:
        # ── Fetch the source ────────────────────────────────────────────
        source = db.get(JobSource, source_uuid)
        if source is None:
            logger.error("JobSource %s not found", source_id)
            return {"status": "failed", "error": "Source not found"}

        # ── Resolve or create the scraping job record ───────────────────
        # When triggered via API (manual scrape / retry), the endpoint
        # pre-creates a ScrapingJob with status=pending and passes its id.
        # When triggered via Celery beat, no job_id is provided and we
        # create the record here.
        if job_id is not None:
            job = db.get(ScrapingJob, uuid.UUID(job_id))
            if job is None:
                logger.error("ScrapingJob %s not found — aborting", job_id)
                return {"status": "failed", "error": "Job record not found"}
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            job.celery_task_id = self.request.id
        else:
            job = ScrapingJob(
                source_id=source_uuid,
                celery_task_id=self.request.id,
                status=JobStatus.running,
                started_at=datetime.now(timezone.utc),
            )
            db.add(job)
        db.commit()
        db.refresh(job)

        try:
            # ── Scrape using the engine ─────────────────────────────────
            from scraper.engine import ScraperEngine

            engine = ScraperEngine()
            scraped_items = _run_async(engine.scrape(source))

            if not scraped_items:
                logger.info("No items scraped for source %s", source_id)
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.leads_found = 0
                db.commit()
                return {"status": "completed", "leads_found": 0}

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
            scoring_service = LeadScoringService()
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

            # ── Finalise the job ────────────────────────────────────────
            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)
            job.leads_found = leads_created
            db.commit()

            logger.info(
                "Scrape completed: source=%s, leads=%d", source_id, leads_created
            )
            return {"status": "completed", "leads_found": leads_created}

        except Exception as exc:
            db.rollback()
            logger.exception(
                "Scrape failed for source %s: %s", source_id, exc
            )

            # Mark job as failed
            job = db.get(ScrapingJob, job.id)
            if job is not None:
                job.status = JobStatus.failed
                job.error_message = str(exc)[:2000]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()

            # Retry with exponential back-off (handled by Celery)
            raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Task 2 – (Re-)score a single lead
# ---------------------------------------------------------------------------
@celery_app.task(
    name="app.workers.tasks.score_lead_task",
)
def score_lead_task(lead_id: str) -> dict:
    """Score an individual lead using the AI scoring service.

    Returns ``{"status": "completed", "lead_id": ..., "score": ...}``.
    """
    lead_uuid = uuid.UUID(lead_id)

    with SyncSessionLocal() as db:
        lead = db.get(Lead, lead_uuid)
        if lead is None:
            logger.error("Lead %s not found for scoring", lead_id)
            return {"status": "failed", "error": "Lead not found"}

        try:
            scoring_service = LeadScoringService()
            lead_data = {
                "title": lead.title,
                "company": lead.company,
                "location": lead.location,
                "salary": lead.salary,
                "description": lead.description,
                "requirements": lead.requirements,
                "platform": lead.platform,
            }

            score = _run_async(scoring_service.score_lead(lead_data))
            lead.score = score
            db.commit()

            logger.info("Lead %s scored: %.1f", lead_id, score)
            return {"status": "completed", "lead_id": str(lead_uuid), "score": score}

        except Exception as exc:
            db.rollback()
            logger.exception("Error scoring lead %s: %s", lead_id, exc)
            return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# Task 3 – Generate an export file (CSV / JSON)
# ---------------------------------------------------------------------------
@celery_app.task(
    name="app.workers.tasks.generate_export_task",
)
def generate_export_task(export_id: str, filters: dict | None = None, format: str = "csv") -> dict:
    """Build an export file and persist the path in the ``Export`` record.

    Parameters
    ----------
    export_id:
        UUID of the ``Export`` row to update.
    filters:
        Optional dict of query filters (``min_score``, ``status``, etc.).
    format:
        ``"csv"`` or ``"json"``.
    """
    export_uuid = uuid.UUID(export_id)
    filters = filters or {}

    with SyncSessionLocal() as db:
        export_record = db.get(Export, export_uuid)
        if export_record is None:
            logger.error("Export %s not found", export_id)
            return {"status": "failed", "error": "Export not found"}

        try:
            # ── Query leads with optional filters ───────────────────────
            query = select(Lead).where(Lead.source_id.isnot(None))

            if "min_score" in filters:
                query = query.where(Lead.score >= float(filters["min_score"]))
            if "max_score" in filters:
                query = query.where(Lead.score <= float(filters["max_score"]))
            if "status" in filters:
                query = query.where(Lead.status == filters["status"])
            if "platform" in filters:
                query = query.where(Lead.platform == filters["platform"])

            # Order by score descending
            query = query.order_by(Lead.score.desc())

            result = db.execute(query)
            leads = result.scalars().all()

            # Convert ORM objects to dicts
            leads_data = []
            for lead in leads:
                leads_data.append({
                    "title": lead.title,
                    "company": lead.company,
                    "location": lead.location,
                    "salary": lead.salary,
                    "platform": lead.platform.value
                    if hasattr(lead.platform, "value")
                    else str(lead.platform),
                    "status": lead.status.value
                    if hasattr(lead.status, "value")
                    else str(lead.status),
                    "score": lead.score,
                    "url": lead.url,
                    "posted_date": lead.created_at,
                })

            # ── Generate the file ───────────────────────────────────────
            export_svc = ExportService()

            if format.lower() == "json":
                file_path = _run_async(
                    export_svc.generate_json(leads_data)
                )
            else:
                file_path = _run_async(
                    export_svc.generate_csv(leads_data)
                )

            # ── Update the export record ────────────────────────────────
            export_record.file_url = file_path
            db.commit()

            logger.info(
                "Export %s generated: %d leads → %s",
                export_id,
                len(leads_data),
                file_path,
            )
            return {
                "status": "completed",
                "export_id": export_id,
                "file_url": file_path,
                "leads_count": len(leads_data),
            }

        except Exception as exc:
            db.rollback()
            logger.exception("Export generation failed for %s: %s", export_id, exc)
            return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# Task 4 – Periodic cleanup of old export files
# ---------------------------------------------------------------------------
@celery_app.task(
    name="app.workers.tasks.cleanup_old_exports_task",
)
def cleanup_old_exports_task() -> dict:
    """Remove export files older than 7 days from disk.

    Returns ``{"status": "completed", "files_removed": <int>}``.
    """
    try:
        export_svc = ExportService()
        removed = export_svc.cleanup_old_exports(days=7)
        logger.info("Cleanup complete: %d file(s) removed", removed)
        return {"status": "completed", "files_removed": removed}
    except Exception as exc:
        logger.exception("Export cleanup failed: %s", exc)
        return {"status": "failed", "error": str(exc)}
