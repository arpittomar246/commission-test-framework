"""Shared Playwright helpers for every page object.

Page objects expose locators and actions and nothing else -- no assertions
live here, so the tests stay the only place that decides what "correct" means.
All element lookups go through ``data-testid``; nothing depends on CSS classes
or on visible text.
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page

from framework.config import Config, config as default_config


class BasePage:
    """Base class wrapping the testid-driven interactions the pages share."""

    path: str = "/"

    def __init__(self, page: Page, cfg: Config | None = None) -> None:
        self.page = page
        self.config = cfg or default_config
        self.timeout = self.config.timeout * 1000

    # ------------------------------------------------------------ navigation --

    def goto(self, path: str | None = None) -> Self:
        """Open this page (or an explicit path) and wait for the network to settle."""
        target = path if path is not None else self.path
        self.page.goto(f"{self.config.base_url}{target}", wait_until="networkidle")
        return self

    def reload(self) -> Self:
        """Reload the current page."""
        self.page.reload(wait_until="networkidle")
        return self

    # -------------------------------------------------------------- locators --

    def testid(self, testid: str) -> Locator:
        """Locator for a single ``data-testid``."""
        return self.page.get_by_test_id(testid)

    def wait_for_testid(self, testid: str, *, state: str = "visible") -> Locator:
        """Wait for an element to reach ``state`` and return its locator."""
        locator = self.testid(testid)
        locator.wait_for(state=state, timeout=self.timeout)
        return locator

    def is_visible(self, testid: str) -> bool:
        """Whether the element is currently visible."""
        return self.testid(testid).is_visible()

    def count(self, testid_prefix: str) -> int:
        """Count elements whose testid starts with ``testid_prefix``."""
        return self.page.locator(f'[data-testid^="{testid_prefix}"]').count()

    # --------------------------------------------------------------- actions --

    def click_testid(self, testid: str) -> None:
        """Click an element once it is ready."""
        self.wait_for_testid(testid).click()

    def fill_testid(self, testid: str, value: str) -> None:
        """Clear a field and type a value into it."""
        self.wait_for_testid(testid).fill(value)

    def select_testid(self, testid: str, value: str) -> None:
        """Pick an option in a ``<select>`` by its value."""
        self.wait_for_testid(testid).select_option(value)

    def type_testid(self, testid: str, value: str, *, delay: int = 30) -> None:
        """Type key by key -- for inputs that react to each keystroke."""
        field = self.wait_for_testid(testid)
        field.click()
        field.press_sequentially(value, delay=delay)

    # ----------------------------------------------------------------- reads --

    def get_text(self, testid: str) -> str:
        """Trimmed visible text of an element."""
        return (self.wait_for_testid(testid).inner_text() or "").strip()

    def get_value(self, testid: str) -> str:
        """Current value of an input or select."""
        return self.wait_for_testid(testid).input_value()

    def get_attribute(self, testid: str, name: str) -> str | None:
        """Read one attribute off an element."""
        return self.wait_for_testid(testid).get_attribute(name)

    # ---------------------------------------------------------------- toasts --

    def wait_for_toast(self, kind: str = "success") -> str:
        """Wait for a toast of the given kind and return its message."""
        return self.wait_for_testid(f"toast-{kind}").inner_text().strip()

    def toast_count(self, kind: str = "success") -> int:
        """How many toasts of a kind are on screen right now."""
        return self.testid(f"toast-{kind}").count()

    # ---------------------------------------------------------------- modals --

    def modal_is_open(self, testid: str) -> bool:
        """Whether a modal is currently open."""
        return self.testid(testid).get_attribute("data-open") == "true"

    def wait_for_modal(self, testid: str) -> Locator:
        """Wait for a modal to become visible."""
        return self.wait_for_testid(testid)

    def wait_for_modal_closed(self, testid: str) -> None:
        """Wait for a modal to disappear."""
        self.testid(testid).wait_for(state="hidden", timeout=self.timeout)

    # ------------------------------------------------------------------- nav --

    def nav_to(self, section: str) -> None:
        """Click a sidebar link: dashboard, agents, policies or commission."""
        self.click_testid(f"nav-{section}")
        self.page.wait_for_load_state("networkidle")

    def page_title(self) -> str:
        """The heading shown in the top bar."""
        return self.get_text("page-title")
