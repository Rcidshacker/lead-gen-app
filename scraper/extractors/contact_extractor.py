"""Regex-based contact information extractor."""

from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass, field


# ------------------------------------------------------------------
# Compiled regex patterns
# ------------------------------------------------------------------

# Email: standard + common TLDs
_EMAIL_RE: re.Pattern[str] = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Phone: various international formats
_PHONE_PATTERNS: list[re.Pattern[str]] = [
    # +1 (800) 555-0199
    re.compile(r"\+?[\d\s\-().]{7,20}(?:ext\.?\s*\d{1,5})?", re.IGNORECASE),
    # 800-555-0199
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # +44 20 7946 0958
    re.compile(r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"),
    # (xxx) xxx-xxxx
    re.compile(r"\(\d{2,4}\)\s*\d{3}[\s\-]\d{4}"),
]

# Social URL patterns
_SOCIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "linkedin": re.compile(
        r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?", re.IGNORECASE
    ),
    "twitter": re.compile(
        r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[\w]{1,15}/?", re.IGNORECASE
    ),
    "github": re.compile(
        r"https?://(?:www\.)?github\.com/[\w\-]+/?", re.IGNORECASE
    ),
    "facebook": re.compile(
        r"https?://(?:www\.)?facebook\.com/[\w.\-]+/?", re.IGNORECASE
    ),
    "instagram": re.compile(
        r"https?://(?:www\.)?instagram\.com/[\w.\-]+/?", re.IGNORECASE
    ),
}


@dataclass
class ContactInfo:
    """Structured contact information extracted from text.

    Attributes:
        emails: List of email addresses found.
        phones: List of phone number strings found.
        social_links: Dict mapping platform name to a list of profile URLs.
    """

    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    social_links: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "emails": self.emails,
            "phones": self.phones,
            "social_links": self.social_links,
        }

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when no contact data was extracted."""
        return not self.emails and not self.phones and not self.social_links


class ContactExtractor:
    """Regex-based contact information extractor.

    Scans arbitrary text for email addresses, phone numbers, and social-media
    profile URLs.  All matching is done with compiled regular expressions —
    no external services or APIs are called.

    Example::

        extractor = ContactExtractor()
        info = extractor.extract("Contact us at hr@acme.com or call +1-555-0100")
        assert info.emails == ["hr@acme.com"]
    """

    def __init__(self) -> None:
        self._email_re = _EMAIL_RE
        self._phone_patterns = list(_PHONE_PATTERNS)
        self._social_patterns = {k: v for k, v in _SOCIAL_PATTERNS.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> dict[str, Any]:
        """Extract contact information from *text*.

        Args:
            text: Any free-form text (HTML content, job description, etc.).

        Returns:
            A dict with keys ``emails``, ``phones``, and ``social_links``.
        """
        if not text:
            return ContactInfo().to_dict()

        info = ContactInfo(
            emails=self._extract_emails(text),
            phones=self._extract_phones(text),
            social_links=self._extract_social_links(text),
        )
        return info.to_dict()

    def extract_as_dataclass(self, text: str) -> ContactInfo:
        """Same as :meth:`extract` but returns a :class:`ContactInfo` instance."""
        if not text:
            return ContactInfo()
        return ContactInfo(
            emails=self._extract_emails(text),
            phones=self._extract_phones(text),
            social_links=self._extract_social_links(text),
        )

    # ------------------------------------------------------------------
    # Private extraction methods
    # ------------------------------------------------------------------

    def _extract_emails(self, text: str) -> list[str]:
        """Find all email addresses in *text*."""
        matches = self._email_re.findall(text)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for email in matches:
            lower = email.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(email)
        return unique

    def _extract_phones(self, text: str) -> list[str]:
        """Find all phone numbers in *text*."""
        phones: list[str] = []
        seen: set[str] = set()

        for pattern in self._phone_patterns:
            for match in pattern.finditer(text):
                raw = match.group().strip()
                # Normalise: remove inner parens, extra spaces
                cleaned = re.sub(r"\s{2,}", " ", raw)
                if cleaned not in seen:
                    seen.add(cleaned)
                    phones.append(cleaned)

        return phones

    def _extract_social_links(self, text: str) -> dict[str, list[str]]:
        """Find all social-media profile URLs in *text*."""
        result: dict[str, list[str]] = {}

        for platform, pattern in self._social_patterns.items():
            matches = pattern.findall(text)
            # Deduplicate
            unique: list[str] = []
            seen: set[str] = set()
            for url in matches:
                # Strip trailing slash for normalisation
                normalised = url.rstrip("/")
                if normalised not in seen:
                    seen.add(normalised)
                    unique.append(normalised)
            if unique:
                result[platform] = unique

        return result
