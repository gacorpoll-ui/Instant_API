"""AI-powered schema detector - the brain of InstantAPI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from instantapi.ai.providers import ask_llm_json
from instantapi.ai.schema import (
    AUTO_DETECT_PROMPT,
    GUIDED_EXTRACT_PROMPT,
    SCHEMA_DETECTOR_SYSTEM,
)
from instantapi.config import Config
from instantapi.scraper.browser import ScrapedPage
from instantapi.scraper.extractor import extract_for_llm


class FieldSchema(BaseModel):
    """Schema for a single field in an endpoint."""

    type: str = "string"
    description: str = ""
    example: Any = None


class EndpointSchema(BaseModel):
    """Schema for a detected API endpoint."""

    name: str
    description: str = ""
    method: str = "GET"
    item_count: int = 0
    schema_fields: dict[str, FieldSchema] = {}
    sample_data: list[dict[str, Any]] = []


class DetectionResult(BaseModel):
    """Result of AI schema detection."""

    endpoints: list[EndpointSchema]
    site_description: str = ""
    source_url: str = ""


async def detect_schema(
    page: ScrapedPage,
    config: Config,
    extract_query: str | None = None,
) -> DetectionResult:
    """Detect data schema from a scraped page using AI.

    Args:
        page: The scraped page to analyze.
        config: InstantAPI config with LLM provider details.
        extract_query: Optional natural language query for guided extraction.
            If None, auto-detect mode is used.

    Returns:
        DetectionResult with detected endpoints and schemas.
    """
    # Prepare content for LLM
    extracted = extract_for_llm(page.html)

    hints = ", ".join(extracted.data_hints) if extracted.data_hints else "none detected"

    # Choose prompt based on mode
    if extract_query:
        prompt = GUIDED_EXTRACT_PROMPT.format(
            user_query=extract_query,
            title=page.title,
            url=page.url,
            content=extracted.main_content,
        )
    else:
        prompt = AUTO_DETECT_PROMPT.format(
            title=page.title,
            url=page.url,
            hints=hints,
            content=extracted.main_content,
        )

    # Ask LLM
    raw = await ask_llm_json(
        prompt=prompt,
        config=config,
        system=SCHEMA_DETECTOR_SYSTEM,
    )

    # Parse response into structured result
    return _parse_detection_result(raw, page.url)


def _parse_detection_result(raw: dict | list, source_url: str) -> DetectionResult:
    """Parse raw LLM JSON response into DetectionResult."""
    if isinstance(raw, list):
        raw = {"endpoints": raw, "site_description": ""}

    endpoints: list[EndpointSchema] = []

    for ep_data in raw.get("endpoints", []):
        # Parse schema fields
        schema_fields: dict[str, FieldSchema] = {}
        schema = ep_data.get("schema", {})
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

        for field_name, field_info in properties.items():
            if isinstance(field_info, dict):
                schema_fields[field_name] = FieldSchema(
                    type=field_info.get("type", "string"),
                    description=field_info.get("description", ""),
                    example=field_info.get("example"),
                )
            else:
                schema_fields[field_name] = FieldSchema(type="string", example=field_info)

        endpoints.append(
            EndpointSchema(
                name=_clean_endpoint_name(ep_data.get("name", "data")),
                description=ep_data.get("description", ""),
                method=ep_data.get("method", "GET"),
                item_count=ep_data.get("item_count", 0),
                schema_fields=schema_fields,
                sample_data=ep_data.get("sample_data", []),
            )
        )

    return DetectionResult(
        endpoints=endpoints,
        site_description=raw.get("site_description", ""),
        source_url=source_url,
    )


def _clean_endpoint_name(name: str) -> str:
    """Clean and normalize endpoint name."""
    import re

    # Remove leading slashes, convert spaces/hyphens/slashes to underscores
    name = name.strip().strip("/").lower()
    name = re.sub(r"[\s\-\/]+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Ensure it's not empty
    return name or "data"
