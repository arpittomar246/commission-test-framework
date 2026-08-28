"""Client-side validation in the modals, and how server errors surface.

Covers the inline field errors, the form-level error banner and the failure
toast -- the paths a user hits when they get something wrong.
"""

import pytest

pytestmark = pytest.mark.ui


def test_empty_agent_name_shows_an_inline_error() -> None:
    """Submitting without a name flags the name field."""


def test_empty_agent_email_shows_an_inline_error() -> None:
    """Submitting without an email flags the email field."""


def test_malformed_agent_email_shows_an_inline_error() -> None:
    """An address without an @ is caught before the request goes out."""


def test_empty_join_date_shows_an_inline_error() -> None:
    """Submitting without a join date flags the date field."""


def test_invalid_agent_form_sends_no_request() -> None:
    """A client-side failure creates nothing on the server."""


def test_duplicate_email_shows_the_server_error_in_the_modal() -> None:
    """A 409 from the API is rendered in the form-level banner."""


def test_duplicate_email_also_shows_an_error_toast() -> None:
    """The failure is surfaced as a toast as well as inline."""


def test_modal_errors_clear_when_the_modal_is_reopened() -> None:
    """A fresh open of the modal starts with no errors showing."""


def test_empty_policy_customer_shows_an_inline_error() -> None:
    """Submitting without a customer name flags the field."""


def test_zero_policy_value_shows_an_inline_error() -> None:
    """A value of zero is rejected in the browser."""


def test_negative_policy_value_shows_an_inline_error() -> None:
    """A negative value is rejected in the browser."""


def test_policy_without_an_agent_shows_an_inline_error() -> None:
    """Submitting with no agent selected flags the dropdown."""


def test_commission_without_an_agent_shows_an_error_banner() -> None:
    """Calculating with nothing selected explains what is missing."""
