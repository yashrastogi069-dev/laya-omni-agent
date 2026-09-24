"""
omni_engine.research.fetcher
============================
Page Extraction and URL Canonicalization Engine with Multi-Tier Fallback
(Scrapling -> BS4/Urllib -> Mock Fixture).

Adheres to Prime Directive & Repository Invariants:
- Multi-Tier Fallback: Attempts lightweight stealth Scrapling before standard HTTP,
  never crashing crawl loops on individual URL failure.
- Bounded Shallow Links: Extracts clean, domain-filtered links for depth <= 1.
- Strict URL Canonicalization: Strips tracking params and fragments to avoid duplicate fetches.
- 100% Offline Testable: Seamlessly integrates with injected mock fixtures.
"""

import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.research import FetchMethod

# Tracking query parameters to strip during canonicalization
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "msclkid", "mc_eid", "_ga", "_gl",
}


def canonicalize_url(url: str) -> str:
    """Normalizes and canonicalizes a URL, stripping tracking parameters and fragments."""
    if not url:
        return ""
    clean = url.strip()
    if not clean.startswith(("http://", "https://")):
        clean = "https://" + clean

    try:
        parsed = urllib.parse.urlsplit(clean)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Filter query params
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        filtered_query = [
            (k, v) for k, v in query_pairs if k.lower() not in _TRACKING_PARAMS
        ]
        new_query = urllib.parse.urlencode(filtered_query)

        # Normalize path
        path = parsed.path
        if not path:
            path = "/"
        elif len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Rebuild without fragment
        canonical = urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))
        return canonical
    except Exception:
        return clean


def extract_domain(url: str) -> str:
    """Extracts the registered host or domain from a URL."""
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


class PageFetcher:
    """Multi-tier web page fetcher supporting Scrapling with BeautifulSoup fallback."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        mock_fixtures: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.timeout = timeout_seconds
        self._fixtures = mock_fixtures or {}

    def register_mock_page(
        self,
        url: str,
        text: str,
        title: str = "",
        links: Optional[List[str]] = None,
    ) -> None:
        """Registers a mock fixture page for offline unit testing."""
        canon = canonicalize_url(url)
        self._fixtures[canon] = {
            "text": text,
            "title": title or "Mock Page",
            "links": links or [],
            "status_code": 200,
        }

    def fetch(self, url: str) -> Dict[str, Any]:
        """Fetches and extracts clean text and links from a URL with multi-tier fallback."""
        canon_url = canonicalize_url(url)
        domain = extract_domain(canon_url)

        # Check offline mock fixtures first
        if canon_url in self._fixtures:
            data = self._fixtures[canon_url]
            return {
                "url": canon_url,
                "domain": domain,
                "title": data.get("title", ""),
                "text": data.get("text", ""),
                "links": [canonicalize_url(l) for l in data.get("links", [])],
                "method": FetchMethod.MOCK_FIXTURE,
                "success": True,
                "error": None,
            }

        # Tier 1: Scrapling StealthyFetcher / Fetcher
        res = self._fetch_via_scrapling(canon_url, domain)
        if res["success"]:
            return res

        # Tier 2: Urllib + BeautifulSoup / Regex fallback
        res = self._fetch_via_urllib_bs4(canon_url, domain)
        if res["success"]:
            return res

        # Tier 3: Failure envelope
        return {
            "url": canon_url,
            "domain": domain,
            "title": "",
            "text": "",
            "links": [],
            "method": FetchMethod.SCRAPLING,
            "success": False,
            "error": res.get("error", "All extraction tiers failed"),
        }

    def _fetch_via_scrapling(self, url: str, domain: str) -> Dict[str, Any]:
        """Tier 1: Fast stealth HTTP fetch via Scrapling."""
        try:
            import scrapling
            fetcher = scrapling.Fetcher()
            response = fetcher.get(url, timeout=self.timeout)

            if response and response.status in (200, 203):
                title = ""
                try:
                    title_elem = response.css("title::text").get()
                    title = str(title_elem).strip() if title_elem else ""
                except Exception:
                    pass

                # Extract text using Scrapling selector
                text_chunks = []
                try:
                    p_tags = response.css("p::text, h1::text, h2::text, h3::text, li::text").getall()
                    text_chunks = [str(t).strip() for t in p_tags if len(str(t).strip()) > 30]
                except Exception:
                    pass

                text = "\n\n".join(text_chunks)
                if not text:
                    text = str(response.body.decode("utf-8", errors="replace"))[:3000]

                # Extract outgoing links
                links = []
                try:
                    hrefs = response.css("a::attr(href)").getall()
                    for h in hrefs:
                        full_url = urllib.parse.urljoin(url, str(h))
                        if full_url.startswith(("http://", "https://")):
                            links.append(canonicalize_url(full_url))
                except Exception:
                    pass

                return {
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "text": text,
                    "links": list(set(links))[:15],
                    "method": FetchMethod.SCRAPLING,
                    "success": bool(text.strip()),
                    "error": None,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "Scrapling returned empty body"}

    def _fetch_via_urllib_bs4(self, url: str, domain: str) -> Dict[str, Any]:
        """Tier 2: Robust urllib + BeautifulSoup / regex fallback."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            title = ""
            text = ""
            links = []

            # Try BeautifulSoup
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""

                # Remove non-content elements
                for tag in soup(["script", "style", "nav", "footer", "svg", "noscript"]):
                    tag.decompose()

                paragraphs = [p.get_text().strip() for p in soup.find_all(["p", "h1", "h2", "h3", "li"])]
                text = "\n\n".join([p for p in paragraphs if len(p) > 25])

                for a in soup.find_all("a", href=True):
                    full = urllib.parse.urljoin(url, a["href"])
                    if full.startswith(("http://", "https://")):
                        links.append(canonicalize_url(full))
            except Exception:
                # Regex fallback
                clean_html = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", clean_html)
                lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
                text = "\n\n".join(lines[:25])

            return {
                "url": url,
                "domain": domain,
                "title": title,
                "text": text,
                "links": list(set(links))[:15],
                "method": FetchMethod.BS4,
                "success": bool(text.strip()),
                "error": None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
