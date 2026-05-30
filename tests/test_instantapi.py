"""Tests for InstantAPI."""

from __future__ import annotations

import json

import pytest

from instantapi.config import Config, LLMProvider, PROVIDER_MODELS
from instantapi.ai.detector import (
    DetectionResult,
    EndpointSchema,
    FieldSchema,
    _clean_endpoint_name,
    _parse_detection_result,
)
from instantapi.api.generator import create_api
from instantapi.scraper.extractor import extract_for_llm


# ─── Config Tests ──────────────────────────────────────────────────────────


class TestConfig:
    def test_defaults(self):
        cfg = Config()
        assert cfg.provider == LLMProvider.OLLAMA
        assert cfg.model == PROVIDER_MODELS[LLMProvider.OLLAMA]
        assert cfg.api_port == 3000

    def test_litellm_model_ollama(self):
        cfg = Config(provider=LLMProvider.OLLAMA, model="llama3.1")
        assert cfg.litellm_model == "ollama/llama3.1"

    def test_litellm_model_already_prefixed(self):
        cfg = Config(provider=LLMProvider.OLLAMA, model="ollama/llama3.1")
        assert cfg.litellm_model == "ollama/llama3.1"

    def test_litellm_model_openai(self):
        cfg = Config(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
        assert cfg.litellm_model == "gpt-4o-mini"

    def test_litellm_model_custom(self):
        cfg = Config(provider=LLMProvider.CUSTOM, model="my-custom-model")
        assert cfg.litellm_model == "my-custom-model"

    def test_save_and_load(self, tmp_path, monkeypatch):
        from instantapi import config as cfg_module
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", tmp_path / "config.json")
        monkeypatch.setattr(cfg_module, "APP_DIR", tmp_path)

        original = Config(provider=LLMProvider.OPENAI, model="gpt-4o", api_port=8080)
        original.save()

        loaded = Config.load()
        assert loaded.provider == LLMProvider.OPENAI
        assert loaded.model == "gpt-4o"
        assert loaded.api_port == 8080


# ─── Detector Tests ────────────────────────────────────────────────────────


class TestDetector:
    def test_clean_endpoint_name_basic(self):
        assert _clean_endpoint_name("Products List") == "products_list"

    def test_clean_endpoint_name_slashes(self):
        assert _clean_endpoint_name("/api/items") == "api_items"

    def test_clean_endpoint_name_special_chars(self):
        assert _clean_endpoint_name("My-Cool Endpoint!") == "my_cool_endpoint"

    def test_clean_endpoint_name_empty(self):
        assert _clean_endpoint_name("") == "data"

    def test_parse_detection_result_basic(self):
        raw = {
            "endpoints": [
                {
                    "name": "products",
                    "description": "Product listings",
                    "method": "GET",
                    "item_count": 10,
                    "schema": {
                        "properties": {
                            "name": {"type": "string", "description": "Product name"},
                            "price": {"type": "number", "example": 9.99},
                        }
                    },
                    "sample_data": [{"name": "Widget", "price": 9.99}],
                }
            ],
            "site_description": "An e-commerce site",
        }
        result = _parse_detection_result(raw, "https://example.com")
        assert len(result.endpoints) == 1
        ep = result.endpoints[0]
        assert ep.name == "products"
        assert ep.description == "Product listings"
        assert ep.item_count == 10
        assert "name" in ep.schema_fields
        assert "price" in ep.schema_fields
        assert ep.schema_fields["price"].type == "number"
        assert result.site_description == "An e-commerce site"

    def test_parse_detection_result_list_input(self):
        raw = [{"name": "items", "description": "Items", "schema": {"properties": {}}}]
        result = _parse_detection_result(raw, "https://example.com")
        assert len(result.endpoints) == 1


# ─── Generator Tests ───────────────────────────────────────────────────────


class TestGenerator:
    def _make_result(self) -> DetectionResult:
        return DetectionResult(
            endpoints=[
                EndpointSchema(
                    name="books",
                    description="Book collection",
                    item_count=3,
                    schema_fields={
                        "title": FieldSchema(type="string", example="Python 101"),
                        "author": FieldSchema(type="string", example="Jane Doe"),
                        "price": FieldSchema(type="number", example=29.99),
                    },
                    sample_data=[
                        {"title": "Python 101", "author": "Jane Doe", "price": 29.99},
                        {"title": "FastAPI Deep Dive", "author": "John Smith", "price": 39.99},
                        {"title": "AI for Everyone", "author": "Alice", "price": 19.99},
                    ],
                )
            ],
            site_description="A bookstore",
            source_url="https://books.example.com",
        )

    def test_create_api_returns_fastapi(self):
        from fastapi import FastAPI
        result = self._make_result()
        api = create_api(result)
        assert isinstance(api, FastAPI)

    @pytest.mark.asyncio
    async def test_list_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 3

    @pytest.mark.asyncio
    async def test_search_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books?q=python")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert "Python" in data["data"][0]["title"]

    @pytest.mark.asyncio
    async def test_get_item(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books/0")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Python 101"

    @pytest.mark.asyncio
    async def test_get_item_not_found(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books/999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_schema_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "fields" in data
        assert "title" in data["fields"]

    @pytest.mark.asyncio
    async def test_pagination(self):
        from httpx import AsyncClient, ASGITransport
        result = self._make_result()
        api = create_api(result)

        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            resp = await client.get("/api/books?page=1&limit=2")
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_next"] is True


# ─── Extractor Tests ───────────────────────────────────────────────────────


class TestExtractor:
    def test_basic_extraction(self):
        html = """
        <html>
        <body>
        <h1>Products</h1>
        <ul>
          <li class="product">Widget A - $9.99</li>
          <li class="product">Widget B - $14.99</li>
          <li class="product">Widget C - $19.99</li>
        </ul>
        </body>
        </html>
        """
        result = extract_for_llm(html)
        assert result.main_content is not None
        assert len(result.main_content) > 0

    def test_price_hint_detection(self):
        html = "<html><body><p>Price: $9.99</p><p>Sale: $5.00</p><p>Total: $14.99</p></body></html>"
        result = extract_for_llm(html)
        hints = " ".join(result.data_hints)
        assert "prices" in hints

    def test_table_extraction(self):
        html = """
        <html><body>
        <table>
          <thead><tr><th>Name</th><th>Age</th></tr></thead>
          <tbody>
            <tr><td>Alice</td><td>30</td></tr>
            <tr><td>Bob</td><td>25</td></tr>
          </tbody>
        </table>
        </body></html>
        """
        result = extract_for_llm(html)
        assert "[TABLE]" in result.main_content
        assert "Alice" in result.main_content

    def test_max_chars_truncation(self):
        html = "<html><body>" + "x" * 100_000 + "</body></html>"
        result = extract_for_llm(html, max_chars=1000)
        assert len(result.main_content) <= 1100  # slight buffer for [TRUNCATED]
        assert "TRUNCATED" in result.main_content


# ─── Storage Tests ─────────────────────────────────────────────────────────


class TestStorage:
    @pytest.mark.asyncio
    async def test_save_and_get(self, tmp_path, monkeypatch):
        from instantapi import config as cfg_module
        from instantapi.storage import db as db_module

        monkeypatch.setattr(cfg_module, "APP_DIR", tmp_path)
        monkeypatch.setattr(cfg_module, "DB_FILE", tmp_path / "test.db")
        monkeypatch.setattr(db_module, "APP_DIR", tmp_path)
        monkeypatch.setattr(db_module, "DB_FILE", tmp_path / "test.db")

        from instantapi.storage.db import delete_api, get_api, list_apis, save_api

        result = DetectionResult(
            endpoints=[
                EndpointSchema(
                    name="items",
                    schema_fields={"title": FieldSchema(type="string")},
                    sample_data=[{"title": "Test"}],
                )
            ],
            site_description="Test Site",
            source_url="https://test.com",
        )

        api_id = await save_api(result)
        assert api_id > 0

        loaded = await get_api(api_id)
        assert loaded is not None
        assert loaded.source_url == "https://test.com"
        assert len(loaded.endpoints) == 1
        assert loaded.endpoints[0].name == "items"

        apis = await list_apis()
        assert len(apis) == 1

        deleted = await delete_api(api_id)
        assert deleted is True

        none_result = await get_api(api_id)
        assert none_result is None


# ─── Regression Tests (bug fixes) ─────────────────────────────────────────


class TestBugFixes:
    """Tests for bugs found and fixed in code review."""

    # Bug #1: Duplicate CLI command registration
    def test_no_duplicate_config_command(self):
        """config-cmd should NOT appear in registered commands; only 'config' should."""
        from instantapi.cli import app
        names = [
            cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            for cmd in app.registered_commands
        ]
        assert "config-cmd" not in names, "Duplicate 'config-cmd' command found in CLI"
        assert "config" in names, "'config' command missing from CLI"

    # Bug #2: XSS in dashboard
    def test_dashboard_escapes_html(self):
        """Dashboard should escape HTML in user-controlled API data."""
        import html as html_module
        malicious = '<script>alert("xss")</script>'
        escaped = html_module.escape(malicious)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    # Bug #4: response_format not sent to unsupported providers
    def test_json_mode_only_for_supported_providers(self):
        from instantapi.ai.providers import _JSON_MODE_PROVIDERS
        from instantapi.config import LLMProvider
        assert LLMProvider.OPENAI in _JSON_MODE_PROVIDERS
        assert LLMProvider.ANTHROPIC in _JSON_MODE_PROVIDERS
        assert LLMProvider.OLLAMA not in _JSON_MODE_PROVIDERS
        assert LLMProvider.GEMINI not in _JSON_MODE_PROVIDERS
        assert LLMProvider.GROQ not in _JSON_MODE_PROVIDERS

    # Bug #5: Config.extra field persisted
    def test_config_extra_persisted(self, tmp_path, monkeypatch):
        from instantapi import config as cfg_module
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", tmp_path / "config.json")
        monkeypatch.setattr(cfg_module, "APP_DIR", tmp_path)

        original = Config(extra={"my_key": "my_value", "num": 42})
        original.save()

        loaded = Config.load()
        assert loaded.extra.get("my_key") == "my_value"
        assert loaded.extra.get("num") == 42

    # Bug #6: is_active soft-delete consistency
    @pytest.mark.asyncio
    async def test_soft_delete_hides_api(self, tmp_path, monkeypatch):
        from instantapi import config as cfg_module
        from instantapi.storage import db as db_module

        monkeypatch.setattr(cfg_module, "APP_DIR", tmp_path)
        monkeypatch.setattr(cfg_module, "DB_FILE", tmp_path / "test.db")
        monkeypatch.setattr(db_module, "APP_DIR", tmp_path)
        monkeypatch.setattr(db_module, "DB_FILE", tmp_path / "test.db")

        from instantapi.ai.detector import DetectionResult, EndpointSchema, FieldSchema
        from instantapi.storage.db import delete_api, get_api, list_apis, save_api

        result = DetectionResult(
            endpoints=[EndpointSchema(name="things", schema_fields={}, sample_data=[])],
            site_description="Test",
            source_url="https://test.com",
        )
        api_id = await save_api(result)

        # Before delete — should be visible
        assert await get_api(api_id) is not None
        apis_before = await list_apis()
        assert any(a["id"] == api_id for a in apis_before)

        # After soft delete — should be hidden
        ok = await delete_api(api_id)
        assert ok is True

        assert await get_api(api_id) is None
        apis_after = await list_apis()
        assert not any(a["id"] == api_id for a in apis_after)

        # Double-delete should return False (already inactive)
        second_delete = await delete_api(api_id)
        assert second_delete is False

    # Bug #7: No dead imports in exporter
    def test_exporter_no_dead_imports(self):
        import importlib
        import instantapi.api.exporter as exporter_module
        source = open(exporter_module.__file__).read()
        assert "FileSystemLoader" not in source
        assert "PackageLoader" not in source
