"""LLM-powered job data extractor for validating and normalising raw scraped data."""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from loguru import logger
from openai import AsyncOpenAI

from scraper.scrapers.base import BaseScraper


# Required fields that must be present for a job to be considered valid
REQUIRED_FIELDS: set[str] = {"title", "company"}


class JobExtractor:
    """Uses the OpenAI API to parse, validate, and normalise raw scraped data.

    The extractor sends each raw job dict to an LLM with a strict schema
    instruction.  It validates that required fields are non-empty, normalises
    salary strings into a consistent format, and ensures the output conforms
    to the canonical LeadForge job schema.

    Example::

        extractor = JobExtractor()
        normalised = await extractor.extract_from_raw(raw_data)
        batch = await extractor.extract_batch(raw_data_list)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
    ) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY", "")
        )
        self.temperature = temperature
        logger.debug(f"JobExtractor initialised with model={self.model}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract_from_raw(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalise a single raw job dictionary.

        Args:
            raw_data: The raw scraped job data.

        Returns:
            A validated, normalised job dict.

        Raises:
            ValueError: If required fields (``title``, ``company``) are missing
                or empty after LLM extraction.
        """
        # Quick synchronous pre-check
        self._validate_required_fields(raw_data)

        # Ask the LLM to clean / fill gaps
        result = await self._call_llm(raw_data)

        # Validate again after LLM pass
        self._validate_required_fields(result)

        # Normalise salary
        result["salary"] = BaseScraper.parse_salary(str(result.get("salary", "")))

        # Clean all text fields
        for text_field in ("title", "company", "location", "description", "requirements"):
            if text_field in result and isinstance(result[text_field], str):
                result[text_field] = BaseScraper.clean_text(result[text_field])

        return result

    async def extract_batch(
        self, raw_data_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate and normalise multiple raw job dictionaries.

        Items that fail validation are silently skipped and logged as warnings.

        Args:
            raw_data_list: A list of raw scraped job dicts.

        Returns:
            A list of validated, normalised job dicts.
        """
        results: list[dict[str, Any]] = []

        for idx, raw in enumerate(raw_data_list):
            try:
                normalised = await self.extract_from_raw(raw)
                results.append(normalised)
            except ValueError as exc:
                logger.warning(
                    f"Skipping item {idx} — validation error: {exc}"
                )
            except Exception as exc:
                logger.error(f"Error processing item {idx}: {exc}")

        logger.info(
            f"extract_batch: {len(results)}/{len(raw_data_list)} items valid"
        )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_required_fields(self, data: dict[str, Any]) -> None:
        """Raise ``ValueError`` if any required field is missing or empty."""
        for field_name in REQUIRED_FIELDS:
            value = data.get(field_name, "")
            if not value or (isinstance(value, str) and not value.strip()):
                raise ValueError(
                    f"Required field '{field_name}' is missing or empty"
                )

    async def _call_llm(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Send the raw data to the LLM for cleaning and enrichment.

        Returns:
            A parsed JSON dict from the LLM response.
        """
        system_prompt: str = (
            "You are a data-normalisation assistant for a job-board scraper. "
            "Given a raw job listing, clean the data and return a valid JSON "
            "object with these exact fields:\n"
            "\n"
            "- title (string, required)\n"
            "- company (string, required)\n"
            "- location (string)\n"
            "- salary (string — normalise into '<min>-<max> <currency>' format)\n"
            "- description (string — cleaned, full text)\n"
            "- requirements (string — key requirements)\n"
            "- url (string — valid URL)\n"
            "- skills (array of strings)\n"
            "\n"
            "Rules:\n"
            "1. Never invent data that isn't present or clearly implied.\n"
            "2. Clean up HTML tags, escape characters, and whitespace.\n"
            "3. Return ONLY valid JSON — no markdown fences or commentary."
        )

        user_message: str = (
            f"Normalise this raw job listing into the required schema:\n\n"
            f"{json.dumps(raw_data, ensure_ascii=False, default=str)}"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )

            content: str = response.choices[0].message.content or "{}"
            return json.loads(content)

        except json.JSONDecodeError as exc:
            logger.error(f"LLM returned invalid JSON: {exc}")
            # Return the original data as a best-effort fallback
            return raw_data
        except Exception as exc:
            logger.error(f"LLM extraction call failed: {exc}")
            return raw_data
