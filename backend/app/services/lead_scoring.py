"""AI-powered lead scoring and embedding service using OpenAI's GPT models.

Evaluates job postings against configurable criteria and returns a
relevance score between 0 and 100.  Also generates vector embeddings
via ``text-embedding-3-small`` for semantic search.
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
- Job title match & relevance (0-30 points):  How closely does the role
  align with the seeker's desired role / skill set?
- Company reputation signals (0-20 points):  Is the company well-known,
  well-funded, or otherwise attractive?  (Infer from context if needed.)
- Location relevance (0-20 points):  Is the location remote-friendly or
  in the seeker's preferred area?
- Salary competitiveness (0-15 points):  How does the offered compensation
  compare to market rates?  If no salary is listed, assume average (8 pts).
- Requirements alignment (0-15 points):  Does the seeker's experience
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
    """Async service that calls OpenAI to score individual or batch leads
    and generate vector embeddings for semantic search."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialise the OpenAI async client."""
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=getattr(settings, "OPENAI_BASE_URL", None) or None,
            )
        return self._client

    # ------------------------------------------------------------------
    # Public API — Scoring
    # ------------------------------------------------------------------
    async def score_lead(
        self,
        lead_data: dict,
        user_preferences: dict | None = None,
    ) -> float:
        """Score a single lead using the configured LLM.

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
            description=(lead_data.get("description", ""))[:2000],
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
            score = max(0.0, min(100.0, score))

            logger.debug(
                "Scored lead '%s' at %s -> %.1f",
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
        """
        scores: list[float] = []
        for lead in leads:
            score = await self.score_lead(lead, user_preferences)
            scores.append(score)
        return scores

    # ------------------------------------------------------------------
    # Public API — Embeddings
    # ------------------------------------------------------------------
    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate a vector embedding for the given text.

        Uses ``text-embedding-3-small`` which is ~5x cheaper than
        ``text-embedding-ada-002`` and yields higher MTEB accuracy scores.

        Parameters
        ----------
        text:
            The text to embed. Truncated to 8000 characters to stay
            within the model's token limit.

        Returns
        -------
        list[float] | None
            A 1536-dimensional embedding vector, or ``None`` on failure.
        """
        if not text or not text.strip():
            return None

        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return response.data[0].embedding
        except Exception:
            logger.exception("Failed to generate embedding")
            return None

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float] | None]:
        """Generate embeddings for multiple texts in a single API call.

        Uses the ``input`` list parameter to batch requests, reducing
        API calls and cost.

        Parameters
        ----------
        texts:
            List of texts to embed.

        Returns
        -------
        list[list[float] | None]
            Embedding vectors in the same order as *texts*. Entries are
            ``None`` if the individual text was empty.
        """
        if not texts:
            return []

        # Filter out empty texts but track their positions
        indexed_texts = [(i, t[:8000]) for i, t in enumerate(texts) if t and t.strip()]
        if not indexed_texts:
            return [None] * len(texts)

        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=[t for _, t in indexed_texts],
            )

            # Map results back to original positions
            result: list[list[float] | None] = [None] * len(texts)
            for (orig_idx, _), data in zip(indexed_texts, response.data):
                result[orig_idx] = data.embedding

            return result
        except Exception:
            logger.exception("Failed to generate batch embeddings")
            return [None] * len(texts)


# ---------------------------------------------------------------------------
# Singleton for easy import
# ---------------------------------------------------------------------------
lead_scoring_service = LeadScoringService()
