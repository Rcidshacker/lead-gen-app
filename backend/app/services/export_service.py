"""Export service — generates CSV / JSON files from lead data.

Provides:
- ``generate_csv`` — write leads to a CSV file.
- ``generate_json`` — write leads to a JSON file.
- ``cleanup_old_exports`` — remove export files older than N days.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Columns to include in exported files
EXPORT_COLUMNS = [
    "title",
    "company",
    "location",
    "salary",
    "platform",
    "status",
    "score",
    "url",
    "posted_date",
]


class ExportService:
    """Service for generating and managing lead export files."""

    def __init__(self, output_dir: str = "exports") -> None:
        """
        Parameters
        ----------
        output_dir:
            Base directory where generated files are stored.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------
    async def generate_csv(
        self,
        leads_query_result: list[dict],
        output_path: str | None = None,
    ) -> str:
        """Write *leads_query_result* to a CSV file.

        Parameters
        ----------
        leads_query_result:
            List of dicts, each representing a lead row from the DB.
        output_path:
            Absolute or relative path for the output file.  If ``None``,
            a timestamped filename is generated inside *output_dir*.

        Returns
        -------
        str
            The file path of the generated CSV.
        """
        if not leads_query_result:
            logger.warning("generate_csv called with empty data")

        # Normalise each lead dict to only include desired columns
        rows = []
        for lead in leads_query_result:
            # Handle enum values gracefully
            row = {}
            for col in EXPORT_COLUMNS:
                val = lead.get(col)
                if val is not None and hasattr(val, "value"):
                    val = val.value
                row[col] = val
            rows.append(row)

        df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)

        if output_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"leads_export_{timestamp}.csv")

        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info("CSV export written to %s (%d rows)", output_path, len(df))
        return output_path

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------
    async def generate_json(
        self,
        leads_query_result: list[dict],
        output_path: str | None = None,
    ) -> str:
        """Write *leads_query_result* to a JSON file.

        Parameters
        ----------
        leads_query_result:
            List of dicts, each representing a lead row from the DB.
        output_path:
            Absolute or relative path for the output file.  If ``None``,
            a timestamped filename is generated inside *output_dir*.

        Returns
        -------
        str
            The file path of the generated JSON.
        """
        if not leads_query_result:
            logger.warning("generate_json called with empty data")

        # Normalise each lead dict to only include desired columns
        rows = []
        for lead in leads_query_result:
            row = {}
            for col in EXPORT_COLUMNS:
                val = lead.get(col)
                if val is not None and hasattr(val, "value"):
                    val = val.value
                # Convert non-serialisable types
                if isinstance(val, (datetime,)):
                    val = val.isoformat()
                row[col] = val
            rows.append(row)

        if output_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"leads_export_{timestamp}.json")

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, ensure_ascii=False, default=str)

        logger.info("JSON export written to %s (%d rows)", output_path, len(rows))
        return output_path

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def cleanup_old_exports(self, days: int = 7) -> int:
        """Delete export files older than *days*.

        Returns the number of files removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0

        for file_path in self.output_dir.iterdir():
            if not file_path.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=timezone.utc
                )
                if mtime < cutoff:
                    file_path.unlink()
                    removed += 1
                    logger.debug("Removed old export: %s", file_path)
            except OSError as exc:
                logger.warning("Could not remove %s: %s", file_path, exc)

        if removed:
            logger.info("Cleaned up %d old export file(s)", removed)
        return removed


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
export_service = ExportService()
