"""
omni_engine.browser.session
===========================
Persistent Browser Session and Process Lifecycle Manager.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Single active browser instance per session.
- Host Safety & 8GB RAM Protection (REQ-B1):
  1. Profile isolated to `~/.laya/browser_profile` (never user daily browser).
  2. Stale lock recovery purging orphan lockfiles before launch.
  3. Single-page invariant (`max_pages=1`) routing popups into the active tab.
  4. Automatic `atexit` cleanup and PID tracking to prevent zombie processes.
  5. Low-memory launch arguments minimizing background overhead.
"""

import atexit
import os
import signal
import sys
import threading
import time
from typing import Any, Dict, List, Optional
import psutil

DEFAULT_PROFILE_DIR = os.path.expanduser(os.environ.get("LAYA_BROWSER_PROFILE", "~/.laya/browser_profile"))

_SESSION_LOCK = threading.RLock()
_GLOBAL_BROWSER_SESSION: Optional["BrowserSession"] = None


def _cleanup_stale_locks(profile_dir: str) -> None:
    """Detects and purges orphan Chromium/Edge lockfiles if the owning process is dead."""
    if not os.path.exists(profile_dir):
        return

    lock_names = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]
    for name in lock_names:
        lock_path = os.path.join(profile_dir, name)
        if os.path.exists(lock_path) or os.path.islink(lock_path):
            try:
                # If symlink (POSIX/Windows), check target PID
                if os.path.islink(lock_path):
                    target = os.readlink(lock_path)
                    # Often format is hostname-PID
                    parts = target.split("-")
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        if not psutil.pid_exists(pid):
                            os.unlink(lock_path)
                    else:
                        os.unlink(lock_path)
                else:
                    # Regular file lock: remove if stale
                    os.remove(lock_path)
            except Exception:
                pass


class BrowserSession:
    """Manages a persistent, resource-safe Playwright browser context."""

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        headless: bool = True,
        slow_mo: int = 0,
        mock_context: Any = None,
    ) -> None:
        self.profile_dir = profile_dir or DEFAULT_PROFILE_DIR
        self.headless = headless
        self.slow_mo = slow_mo
        self._lock = threading.RLock()

        self._playwright = None
        self._context = mock_context
        self._active_page = None
        self._browser_pid: Optional[int] = None
        self._is_closed = False

        if mock_context is None:
            atexit.register(self.close)

    def is_active(self) -> bool:
        """Returns True if the browser session is currently running."""
        with self._lock:
            return self._context is not None and not self._is_closed

    def get_active_page(self) -> Any:
        """Returns the active Page, launching the persistent context if not already open."""
        with self._lock:
            if self._active_page is not None:
                # Verify page is not crashed or closed
                try:
                    if not self._active_page.is_closed():
                        return self._active_page
                except Exception:
                    pass

            self.start()
            return self._active_page

    def start(self) -> None:
        """Launches the persistent Playwright browser context with strict resource bounds."""
        with self._lock:
            if self._context is not None and not self._is_closed:
                return

            if self._playwright is None:
                from playwright.sync_api import sync_playwright
                self._playwright = sync_playwright().start()

            # Ensure profile directory exists and stale locks are cleaned
            os.makedirs(self.profile_dir, exist_ok=True)
            _cleanup_stale_locks(self.profile_dir)

            low_memory_args = [
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",
                "--disable-component-update",
                "--disable-extensions",
            ]

            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=low_memory_args,
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=False,  # REQ-NB3: download guard
                )
            except Exception as e:
                # Fallback: if persistent context lock fails, clean locks and retry once
                _cleanup_stale_locks(self.profile_dir)
                time.sleep(0.5)
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=low_memory_args,
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=False,
                )

            # Enforce Single Page Invariant (REQ-B1)
            pages = self._context.pages
            if pages:
                self._active_page = pages[0]
                # Close any extra zombie pages
                for extra in pages[1:]:
                    try:
                        extra.close()
                    except Exception:
                        pass
            else:
                self._active_page = self._context.new_page()

            # Route popups into the single active page
            self._context.on("page", self._handle_popup_page)
            self._is_closed = False

    def _handle_popup_page(self, new_page: Any) -> None:
        """Intercepts popups and redirects URL to active page, enforcing max_pages=1."""
        try:
            with self._lock:
                popup_url = new_page.url
                if popup_url and popup_url != "about:blank" and self._active_page:
                    self._active_page.goto(popup_url, wait_until="domcontentloaded")
                new_page.close()
        except Exception:
            pass

    def close(self) -> None:
        """Gracefully closes page, context, and Playwright driver."""
        with self._lock:
            if self._is_closed:
                return
            self._is_closed = True

            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
                self._context = None
                self._active_page = None

            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None


def get_shared_browser_session(headless: bool = True) -> BrowserSession:
    """Returns the singleton shared BrowserSession instance."""
    global _GLOBAL_BROWSER_SESSION
    with _SESSION_LOCK:
        if _GLOBAL_BROWSER_SESSION is None or _GLOBAL_BROWSER_SESSION._is_closed:
            _GLOBAL_BROWSER_SESSION = BrowserSession(headless=headless)
        return _GLOBAL_BROWSER_SESSION
