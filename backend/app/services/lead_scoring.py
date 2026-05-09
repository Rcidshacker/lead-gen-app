"""AI-powered lead scoring service using OpenAI's GPT models.

Evaluates job postings against configurable criteria and returns a
relevance score between 0 and 100.
"""

import json
import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
SCORING_SYSTEM_PROMPT = """\
You are an expert recruitment analyst.  Your job is to score job postings
on a scale from 0 to 100 based on how well they match a job seeker's
profile and preferences.

Scoring criteria (total 100 points):
- Job title match & relevance (0–30 points):  How closely does the role
  align with the seeker's desired role / skill set?
- Company reputation signals (0–20 points):  Is the company well-known,
  well-funded, or otherwise attractive?  (Infer from context if needed.)
- Location relevance (0–20 points):  Is the location remote-friendly or
  in the seeker's preferred area?
- Salary competitiveness (0–15 points):  How does the offered compensation
  compare to market rates?  If no salary is listed, assume average (8 pts).
- Requirements alignment (0–15 points):  Does the seeker's experience
  match the stated requirements?

Respond ONLY with a JSON object: {"score": <integer 0-100>, "reason": "<brief explanation>"}
"""

SCORING_USER_PROMPT = """\
Score the following job posting.  Return a JSON object with "score" (0-100) \
and "reason" (brief justification).

{preferences_block}

--- Job Posting ---
Title: {title}
Company: {company}
Location: {location}
Salary: {salary}
Description: {description}
Requirements: {requirements}
Platform: {platform}
"""


class LeadScoringService:
    """Async service that calls OpenAI to score individual or batch leads."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialise the OpenAI async client."""
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def score_lead(
        self,
        lead_data: dict,
        user_preferences: dict | None = None,
    ) -> float:
        """Score a single lead using GPT-4o-mini.

        Parameters
        ----------
        lead_data:
            Dict with keys: title, company, location, salary, description,
            requirements, platform.
        user_preferences:
            Optional dict with keys like desired_role, preferred_locations,
            min_salary, skills, experience_level.

        Returns
        -------
        float
            Score between 0 and 100.
        """
        preferences_block = ""
        if user_preferences:
            preferences_block = (
                "--- User Preferences ---\n"
                f"Desired role: {user_preferences.get('desired_role', 'N/A')}\n"
                f"Preferred locations: {user_preferences.get('preferred_locations', 'Any')}\n"
                f"Minimum salary: {user_preferences.get('min_salary', 'N/A')}\n"
                f"Skills: {user_preferences.get('skills', 'N/A')}\n"
                f"Experience level: {user_preferences.get('experience_level', 'N/A')}\n"
            )

        user_message = SCORING_USER_PROMPT.format(
            title=lead_data.get("title", ""),
            company=lead_data.get("company", ""),
            location=lead_data.get("location", ""),
            salary=lead_data.get("salary", ""),
            description=(lead_data.get("description", ""))[:2000],  # truncate to limit tokens
            requirements=(lead_data.get("requirements", ""))[:1500],
            platform=lead_data.get("platform", ""),
            preferences_block=preferences_block,
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.SGAI_MODEL,
                temperature=settings.SGAI_TEMPERATURE,
                max_tokens=settings.SGAI_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            score = float(parsed.get("score", 50))
            # Clamp to valid range
            score = max(0.0, min(100.0, score))

            logger.debug(
                "Scored lead '%s' at %s → %.1f",
                lead_data.get("title", "?"),
                lead_data.get("company", "?"),
                score,
            )
            return score

        except json.JSONDecodeError:
            logger.warning("Failed to parse scoring response JSON, defaulting to 50")
            return 50.0
        except Exception:
            logger.exception("Error scoring lead '%s'", lead_data.get("title", "?"))
            return 50.0

    async def score_leads_batch(
        self,
        leads: list[dict],
        user_preferences: dict | None = None,
    ) -> list[float]:
        """Score multiple leads sequentially.

        Returns a list of scores in the same order as *leads*.

        .. note::
            For very large batches consider chunking or running in a
            Celery task to avoid blocking the event loop.
        """
        scores: list[float] = []
        for lead in leads:
            score = await self.score_lead(lead, user_preferences)
            scores.append(score)
        return scores


# ---------------------------------------------------------------------------
# Singleton for easy import
# ---------------------------------------------------------------------------
lead_scoring_service = LeadScoringService()
