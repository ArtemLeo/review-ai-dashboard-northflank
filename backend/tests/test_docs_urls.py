"""Tests for the production switch of the interactive API documentation."""

from main import api_docs_urls


def test_documentation_is_available_outside_production() -> None:
    """Development keeps the Swagger UI page and the OpenAPI schema (ReDoc is never published)."""
    urls = api_docs_urls("development")

    assert urls["docs_url"] == "/docs"
    assert urls["openapi_url"] == "/openapi.json"


def test_documentation_is_disabled_in_production() -> None:
    """Production exposes neither the pages nor the schema."""
    urls = api_docs_urls(" Production ")

    assert urls == {"docs_url": None, "redoc_url": None, "openapi_url": None}
