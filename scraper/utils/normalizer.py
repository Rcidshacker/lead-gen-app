"""URL normalization utilities for consistent deduplication.

Strips tracking parameters, normalizes scheme/host, removes fragments,
and sorts query parameters to produce a canonical URL representation.
"""

from urllib.parse import parse_qsl, urlunparse, urlparse

# Tracking parameters to strip from URLs
_TRACKING_PARAMS = frozenset({
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gclidw",
    "msclkid",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
})

# Query parameters that are safe to keep
_SAFE_PARAMS_HINTS = frozenset({
    "q", "query", "search", "page", "sort", "location", "keywords",
    "job_type", "experience", "salary", "remote", "category",
    "skill", "title", "company", "seniority", "date_posted",
})


def normalize_url(url: str) -> str:
    """Normalize a URL to its canonical form for deduplication.

    Steps performed:
    1. Parse the URL into components.
    2. Lowercase the scheme and netloc.
    3. Remove fragment identifier.
    4. Strip known tracking query parameters.
    5. Sort remaining query parameters alphabetically.
    6. Remove trailing slashes from the path.
    7. Reassemble.

    Parameters
    ----------
    url:
        The URL to normalize.

    Returns
    -------
    str
        The normalized URL. Returns an empty string if the input is empty
        or cannot be parsed.
    """
    if not url or not url.strip():
        return ""

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return url.strip().lower()

    # Lowercase scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove trailing slashes from path
    path = parsed.path.rstrip("/")

    # Strip tracking parameters and sort remaining
    if parsed.query:
        params = parse_qsl(parsed.query, keep_blank_values=True)
        cleaned = [
            (k, v) for k, v in params
            if k.lower() not in _TRACKING_PARAMS
        ]
        # Sort by key for determinism
        cleaned.sort(key=lambda pair: pair[0].lower())
        query = "&".join(f"{k}={v}" for k, v in cleaned)
    else:
        query = ""

    # Remove fragment entirely
    normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))

    return normalized


def generate_content_hash(title: str, company: str, location: str) -> str:
    """Generate a deterministic SHA-256 hash for lead deduplication.

    Creates a hash of ``lowercase(title + company + location)`` with
    whitespace normalized. This provides a content-level dedup signal
    beyond URL matching alone — two identical job postings at different
    URLs will produce the same hash.

    Parameters
    ----------
    title:
        Job title (e.g. "Senior Python Developer").
    company:
        Company name (e.g. "Google").
    location:
        Job location (e.g. "Remote").

    Returns
    -------
    str
        Hex-encoded SHA-256 digest (64 characters).
    """
    import hashlib
    import re

    # Normalize whitespace: collapse multiple spaces, strip, lowercase
    def _normalize(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip()).lower()

    payload = f"{_normalize(title)}|{_normalize(company)}|{_normalize(location)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
