"""
omni_engine.browser
===================
Real Persistent Browser Engine Package.
"""

from .session import BrowserSession, get_shared_browser_session
from .indexer import DOMActionIndexer, FINANCIAL_KEYWORDS_REGEX, FINANCIAL_URL_REGEX
from .driver import BrowserDriver

__all__ = [
    "BrowserSession",
    "get_shared_browser_session",
    "DOMActionIndexer",
    "FINANCIAL_KEYWORDS_REGEX",
    "FINANCIAL_URL_REGEX",
    "BrowserDriver",
]
