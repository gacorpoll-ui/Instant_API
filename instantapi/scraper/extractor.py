"""HTML content extractor - cleans and structures raw HTML for LLM processing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class ExtractedContent:
    """Clean, structured content ready for LLM analysis."""

    title: str
    main_content: str
    repeating_elements: list[str]
    data_hints: list[str]
    estimated_tokens: int


def extract_for_llm(html: str, max_chars: int = 30_000) -> ExtractedContent:
    """Clean HTML and prepare it for LLM schema detection.

    Strips boilerplate, keeps data-rich elements, and identifies
    repeating patterns that likely represent API-able data.

    Args:
        html: Raw HTML string.
        max_chars: Maximum characters to send to LLM.

    Returns:
        ExtractedContent ready for schema detection.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup.find_all(
        ["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "svg"]
    ):
        tag.decompose()

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Find the main content area
    main = soup.find("main") or soup.find("article") or soup.find(id="content") or soup.body
    if not main:
        main = soup

    # Identify repeating elements (likely data patterns)
    repeating = _find_repeating_patterns(main)

    # Build clean text representation with structure hints
    content_parts: list[str] = []

    # Tables are high-value data
    for table in main.find_all("table"):
        content_parts.append(f"[TABLE]\n{_table_to_text(table)}\n[/TABLE]")

    # Repeating divs/articles/list items
    for pattern_html in repeating:
        content_parts.append(f"[REPEATING_ELEMENT]\n{pattern_html}\n[/REPEATING_ELEMENT]")

    # Remaining text
    remaining = main.get_text(separator="\n", strip=True)
    content_parts.append(remaining)

    main_content = "\n\n".join(content_parts)

    # Truncate if too long
    if len(main_content) > max_chars:
        main_content = main_content[:max_chars] + "\n... [TRUNCATED]"

    # Data hints - clues about what kind of data is on the page
    hints = _detect_data_hints(main)

    return ExtractedContent(
        title=title,
        main_content=main_content,
        repeating_elements=repeating[:10],  # Max 10 examples
        data_hints=hints,
        estimated_tokens=len(main_content) // 4,
    )


def _find_repeating_patterns(root) -> list[str]:
    """Find HTML elements that repeat with similar structure.

    These are likely data items (products, posts, cards, etc.)
    """
    patterns: list[str] = []

    # Look for common repeating containers
    for container_tag in ["article", "li", "tr", "div", "section"]:
        elements = root.find_all(container_tag, recursive=True)
        if len(elements) < 3:
            continue

        # Group by CSS class
        class_groups: dict[str, list] = {}
        for el in elements:
            classes = el.get("class", [])
            key = " ".join(classes) if classes else f"_no_class_{container_tag}"
            class_groups.setdefault(key, []).append(el)

        for key, group in class_groups.items():
            if len(group) >= 3:  # 3+ similar elements = likely data
                # Take first 3 as examples
                for el in group[:3]:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 20:  # Skip tiny elements
                        patterns.append(text[:500])

    return patterns


def _table_to_text(table) -> str:
    """Convert HTML table to readable text format."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _detect_data_hints(root) -> list[str]:
    """Detect hints about what kind of data is on the page."""
    hints: list[str] = []
    text = root.get_text(separator=" ", strip=True).lower()
    if len(text) > 30000:
        text = text[:30000]

    hint_patterns = {
        "prices": r"\$\d+\.?\d*",
        "emails": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "dates": r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}",
        "ratings": r"\d\.?\d*/5|\d\.?\d* stars?",
        "phone_numbers": r"\+?\d[\d\s-]{8,}",
        "percentages": r"\d+\.?\d*%",
    }

    for hint_name, pattern in hint_patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            hints.append(f"{hint_name}: found {len(matches)} instances")

    # Check for common data structures
    tables = root.find_all("table")
    if tables:
        hints.append(f"tables: {len(tables)} found")

    lists = root.find_all(["ul", "ol"])
    data_lists = [l for l in lists if len(l.find_all("li", recursive=False)) >= 3]
    if data_lists:
        hints.append(f"data_lists: {len(data_lists)} found")

    return hints
