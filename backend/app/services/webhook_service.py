"""Webhook dispatch service — sends lead data to configured external webhooks.

Each webhook delivery includes:
- ``X-LeadForge-Event`` header identifying the event type.
- ``X-LeadForge-Signature`` header containing an HMAC-SHA256 signature so
  the receiver can verify authenticity.
"""

import hashlib
import hmac
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Dispatch lead events to one or more webhook URLs."""

    def __init__(self) -> None:
        self._webhook_urls: list[str] = list(settings.WEBHOOK_URLS)
        self._secret: str = settings.WEBHOOK_SECRET

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def dispatch(
        self,
        lead_data: dict,
        event: str,
    ) -> bool:
        """Send *lead_data* to every configured webhook URL.

        Parameters
        ----------
        lead_data:
            The lead payload to forward (will be JSON-encoded).
        event:
            Event identifier, e.g. ``"lead.created"``, ``"lead.updated"``.

        Returns
        -------
        bool
            ``True`` if ALL webhooks returned a 2xx status, ``False`` if
            any delivery failed.
        """
        if not self._webhook_urls:
            logger.debug("No webhook URLs configured — skipping dispatch")
            return True

        payload = json.dumps(lead_data, default=str, ensure_ascii=False)
        signature = self._sign(payload)

        headers = {
            "Content-Type": "application/json",
            "X-LeadForge-Event": event,
            "X-LeadForge-Signature": f"sha256={signature}",
        }

        all_ok = True
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in self._webhook_urls:
                try:
                    response = await client.post(url, content=payload, headers=headers)
                    if response.is_success:
                        logger.info(
                            "Webhook delivered to %s (event=%s, status=%d)",
                            url,
                            event,
                            response.status_code,
                        )
                    else:
                        logger.warning(
                            "Webhook %s returned HTTP %d for event %s: %s",
                            url,
                            response.status_code,
                            event,
                            response.text[:500],
                        )
                        all_ok = False
                except httpx.HTTPError as exc:
                    logger.error(
                        "Failed to deliver webhook to %s for event %s: %s",
                        url,
                        event,
                        exc,
                    )
                    all_ok = False

        return all_ok

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _sign(self, payload: str) -> str:
        """Generate an HMAC-SHA256 hex digest of *payload*."""
        if not self._secret:
            return ""
        mac = hmac.new(
            self._secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        )
        return mac.hexdigest()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
webhook_service = WebhookService()
