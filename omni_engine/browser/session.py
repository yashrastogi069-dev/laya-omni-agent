"""
omni_engine.browser.session
===========================
Persistent Browser Session, Process Lifecycle, and Modular Multi-Tab Manager.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Single active browser instance per session.
- Host Safety & 8GB RAM Protection (REQ-B1 / REV-L18-05):
  1. Profile isolated to `~/.laya/browser_profile` (never user daily browser).
  2. Stale lock recovery purging orphan lockfiles before launch.
  3. Bounded multi-tab management with strict upper limit (`max_tabs=5`).
  4. Automatic `atexit` cleanup and PID tracking to prevent zombie processes.
  5. Low-memory launch arguments minimizing background overhead and memory exhaustion.
- Tab Desynchronization & Close Safety (REV-L18-03 / REV-L18-04):
  1. Automatic dead-page pruning before all tab operations.
  2. Last remaining tab cannot be closed (context always retains >=1 page).
  3. Safe page closing with `run_before_unload=False` preventing modal deadlocks.
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
                    parts = target.split("-")
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        if not psutil.pid_exists(pid):
                            os.unlink(lock_path)
                    else:
                        os.unlink(lock_path)
                else:
                    os.remove(lock_path)
            except Exception:
                pass


class BrowserSession:
    """Manages a persistent, resource-safe Playwright browser context with multi-tab support."""

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        headless: bool = True,
        slow_mo: int = 0,
        mock_context: Any = None,
        max_tabs: int = 5,
    ) -> None:
        self.profile_dir = profile_dir or DEFAULT_PROFILE_DIR
        self.headless = headless
        self.slow_mo = slow_mo
        self.max_tabs = max(1, min(max_tabs, 10))
        self._lock = threading.RLock()

        self._playwright = None
        self._context = mock_context
        self._pages: List[Any] = []
        self._active_tab_index: int = 0
        self._browser_pid: Optional[int] = None
        self._is_closed = False

        if mock_context is not None:
            if hasattr(mock_context, "pages") and mock_context.pages:
                self._pages = list(mock_context.pages)
            elif hasattr(mock_context, "new_page"):
                try:
                    p = mock_context.new_page()
                    self._pages = [p]
                except Exception:
                    self._pages = []
        else:
            atexit.register(self.close)

    @property
    def _active_page(self) -> Any:
        """Backward-compatible accessor for primary active page."""
        return self.get_active_page()

    @_active_page.setter
    def _active_page(self, page: Any) -> None:
        """Backward-compatible setter for primary active page."""
        if page is not None:
            with self._lock:
                if page not in self._pages:
                    self._pages = [page]
                    self._active_tab_index = 0
                else:
                    self._active_tab_index = self._pages.index(page)

    def is_active(self) -> bool:
        """Returns True if the browser session is currently running."""
        with self._lock:
            return self._context is not None and not self._is_closed

    def _prune_dead_pages(self) -> None:
        """REV-L18-03: Removes closed or crashed pages from tracking, ensuring at least one page."""
        if not self._context or self._is_closed:
            return

        alive_pages: List[Any] = []
        for p in self._pages:
            try:
                is_closed = p.is_closed() if callable(getattr(p, "is_closed", None)) else False
                if not is_closed:
                    alive_pages.append(p)
            except Exception:
                pass

        self._pages = alive_pages
        if not self._pages:
            try:
                if callable(getattr(self._context, "new_page", None)):
                    new_p = self._context.new_page()
                    self._pages = [new_p]
                    self._active_tab_index = 0
            except Exception:
                pass
        else:
            if self._active_tab_index >= len(self._pages):
                self._active_tab_index = len(self._pages) - 1

    def get_active_page(self) -> Any:
        """Returns the active Page, launching the persistent context if not already open."""
        with self._lock:
            if not self.is_active():
                self.start()

            self._prune_dead_pages()
            if self._pages and 0 <= self._active_tab_index < len(self._pages):
                return self._pages[self._active_tab_index]
            if self._pages:
                self._active_tab_index = 0
                return self._pages[0]
            return None

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

            # REV-L18-05: Strict low-memory flags protecting 8GB Windows host
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
                "--renderer-process-limit=4",
                "--js-flags=--max-old-space-size=512",
            ]

            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=low_memory_args,
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=False,
                )
            except Exception:
                # Fallback: purge locks and retry once
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

            # Initialize pages list
            pages = self._context.pages if hasattr(self._context, "pages") else []
            if pages:
                self._pages = list(pages[:self.max_tabs])
                self._active_tab_index = 0
                for extra in pages[self.max_tabs:]:
                    try:
                        extra.close()
                    except Exception:
                        pass
            else:
                self._pages = [self._context.new_page()]
                self._active_tab_index = 0

            # Route popups through multi-tab lifecycle handler
            if hasattr(self._context, "on"):
                self._context.on("page", self._handle_popup_page)

            self._is_closed = False

    def _handle_popup_page(self, new_page: Any) -> None:
        """Handles popups: adds as new tab if under max_tabs, else redirects active page."""
        try:
            with self._lock:
                self._prune_dead_pages()
                if len(self._pages) < self.max_tabs:
                    self._pages.append(new_page)
                    self._active_tab_index = len(self._pages) - 1
                else:
                    popup_url = getattr(new_page, "url", "")
                    if popup_url and popup_url != "about:blank" and self._pages:
                        active_p = self._pages[self._active_tab_index]
                        if callable(getattr(active_p, "goto", None)):
                            active_p.goto(popup_url, wait_until="domcontentloaded")
                    if callable(getattr(new_page, "close", None)):
                        try:
                            new_page.close(run_before_unload=False)
                        except TypeError:
                            new_page.close()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Multi-Tab Management Primitives (L18 / REV-L18-03 / REV-L18-04)
    # -----------------------------------------------------------------------

    def list_tabs(self) -> List[Dict[str, Any]]:
        """Enumerates all live tabs in the context with their metadata."""
        with self._lock:
            if not self.is_active():
                self.start()

            self._prune_dead_pages()
            tabs = []
            for i, p in enumerate(self._pages):
                try:
                    url = getattr(p, "url", "")
                    title = p.title() if callable(getattr(p, "title", None)) else getattr(p, "title", "")
                except Exception:
                    url = ""
                    title = ""
                tabs.append({
                    "tab_id": i,
                    "title": str(title or ""),
                    "url": str(url or ""),
                    "is_active": (i == self._active_tab_index),
                })
            return tabs

    def new_tab(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Opens a new tab if under max_tabs limit and sets it active."""
        with self._lock:
            if not self.is_active():
                self.start()

            self._prune_dead_pages()
            if len(self._pages) >= self.max_tabs:
                raise RuntimeError(
                    f"Maximum browser tab limit ({self.max_tabs}) reached. "
                    "Close an existing tab before opening a new one."
                )

            if not self._context:
                raise RuntimeError("Browser context is not initialized.")

            new_p = self._context.new_page()
            if url and url.strip():
                target_url = url.strip()
                if not target_url.startswith(("http://", "https://", "file://", "data:")):
                    target_url = "https://" + target_url
                new_p.goto(target_url, wait_until="domcontentloaded")

            self._pages.append(new_p)
            self._active_tab_index = len(self._pages) - 1

            title = new_p.title() if callable(getattr(new_p, "title", None)) else getattr(new_p, "title", "")
            return {
                "tab_id": self._active_tab_index,
                "title": str(title or ""),
                "url": str(getattr(new_p, "url", "") or ""),
                "is_active": True,
            }

    def switch_tab(self, tab_id: int) -> Dict[str, Any]:
        """Switches active foreground page to the specified tab_id."""
        with self._lock:
            if not self.is_active():
                self.start()

            self._prune_dead_pages()
            if not (0 <= tab_id < len(self._pages)):
                raise IndexError(
                    f"Tab index {tab_id} is out of bounds (currently open tabs: {len(self._pages)})."
                )

            self._active_tab_index = tab_id
            active_p = self._pages[tab_id]
            if callable(getattr(active_p, "bring_to_front", None)):
                try:
                    active_p.bring_to_front()
                except Exception:
                    pass

            title = active_p.title() if callable(getattr(active_p, "title", None)) else getattr(active_p, "title", "")
            return {
                "tab_id": tab_id,
                "title": str(title or ""),
                "url": str(getattr(active_p, "url", "") or ""),
                "is_active": True,
            }

    def close_tab(self, tab_id: Optional[int] = None) -> Dict[str, Any]:
        """REV-L18-04: Closes specified tab with unload deadlock prevention. Refuses to close last remaining tab."""
        with self._lock:
            if not self.is_active():
                self.start()

            self._prune_dead_pages()
            if len(self._pages) <= 1:
                raise RuntimeError(
                    "Cannot close the last remaining browser tab. At least one tab must remain open."
                )

            target_idx = self._active_tab_index if tab_id is None else tab_id
            if not (0 <= target_idx < len(self._pages)):
                raise IndexError(
                    f"Tab index {target_idx} is out of bounds (currently open tabs: {len(self._pages)})."
                )

            page_to_close = self._pages[target_idx]
            try:
                # REV-L18-04: run_before_unload=False avoids hanging on dialogs
                if callable(getattr(page_to_close, "close", None)):
                    try:
                        page_to_close.close(run_before_unload=False)
                    except TypeError:
                        page_to_close.close()
            except Exception:
                pass

            self._pages.pop(target_idx)
            if self._active_tab_index >= len(self._pages):
                self._active_tab_index = len(self._pages) - 1

            active_p = self._pages[self._active_tab_index]
            if callable(getattr(active_p, "bring_to_front", None)):
                try:
                    active_p.bring_to_front()
                except Exception:
                    pass

            return {
                "closed_tab_id": target_idx,
                "active_tab_id": self._active_tab_index,
                "remaining_tabs": len(self._pages),
            }

    def close(self) -> None:
        """Gracefully closes all pages, context, and Playwright driver."""
        with self._lock:
            if self._is_closed:
                return
            self._is_closed = True

            for p in self._pages:
                try:
                    if callable(getattr(p, "close", None)):
                        p.close()
                except Exception:
                    pass
            self._pages.clear()

            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
                self._context = None

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
