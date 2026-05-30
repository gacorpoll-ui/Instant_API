"""Playwright-based web scraper engine."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class ScrapedPage:
    """Result of scraping a single page."""

    url: str
    title: str
    html: str
    text: str
    links: list[str]
    tables: list[list[dict[str, str]]]
    lists: list[list[str]]
    meta: dict[str, str]


@dataclass
class ScrapedSite:
    """Result of scraping a website (potentially multiple pages)."""

    url: str
    pages: list[ScrapedPage]

    @property
    def primary(self) -> ScrapedPage:
        return self.pages[0]


class BrowserScraper:
    """Headless browser scraper powered by Playwright."""

    def __init__(self, timeout: int = 30, headless: bool = True) -> None:
        self.timeout = timeout * 1000  # Playwright uses ms
        self.headless = headless
        self._browser: Browser | None = None

    async def __aenter__(self) -> BrowserScraper:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._browser:
            await self._browser.close()
        await self._pw.stop()

    async def scrape(self, url: str, wait_for: str | None = None) -> ScrapedPage:
        """Scrape a single page.

        Args:
            url: The URL to scrape.
            wait_for: Optional CSS selector to wait for before extracting.

        Returns:
            ScrapedPage with extracted content.
        """
        if not self._browser:
            raise RuntimeError("Scraper not initialized. Use 'async with BrowserScraper() as s:'")

        page = await self._browser.new_page()
        try:
            # Navigate with smart waiting
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.timeout)

            # Wait a bit for dynamic content
            await page.wait_for_timeout(1000)

            # Get full HTML
            html = await page.content()
            title = await page.title()

            # Extract structured data
            soup = BeautifulSoup(html, "html.parser")

            # Clean the HTML - remove scripts, styles, nav, footer
            for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()

            clean_text = soup.get_text(separator="\n", strip=True)
            # Collapse multiple blank lines
            lines = [line for line in clean_text.split("\n") if line.strip()]
            clean_text = "\n".join(lines)

            # Extract tables
            tables = self._extract_tables(soup)

            # Extract lists
            lists = self._extract_lists(soup)

            # Extract links
            links = self._extract_links(soup, url)

            # Extract meta
            meta = self._extract_meta(soup)

            return ScrapedPage(
                url=url,
                title=title,
                html=str(soup),
                text=clean_text,
                links=links,
                tables=tables,
                lists=lists,
                meta=meta,
            )
        finally:
            await page.close()

    async def scrape_site(
        self, url: str, max_pages: int = 1, follow_links: bool = False
    ) -> ScrapedSite:
        """Scrape a website, optionally following links.

        Args:
            url: Starting URL.
            max_pages: Maximum number of pages to scrape.
            follow_links: Whether to follow internal links.

        Returns:
            ScrapedSite with all scraped pages.
        """
        pages: list[ScrapedPage] = []
        visited: set[str] = set()
        to_visit: list[str] = [url]
        base_domain = urlparse(url).netloc

        while to_visit and len(pages) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            page = await self.scrape(current_url)
            pages.append(page)

            if follow_links:
                for link in page.links:
                    parsed = urlparse(link)
                    if parsed.netloc == base_domain and link not in visited:
                        to_visit.append(link)

        return ScrapedSite(url=url, pages=pages)

    @staticmethod
    def _extract_tables(soup: BeautifulSoup) -> list[list[dict[str, str]]]:
        """Extract HTML tables as list of row dicts."""
        tables = []
        for table in soup.find_all("table"):
            headers: list[str] = []
            rows: list[dict[str, str]] = []

            # Get headers
            thead = table.find("thead")
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all(["th", "td"])]
            else:
                first_row = table.find("tr")
                if first_row:
                    ths = first_row.find_all("th")
                    if ths:
                        headers = [th.get_text(strip=True) for th in ths]

            # Get data rows
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and cells != headers:
                    if headers and len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells)))
                    elif cells:
                        rows.append({f"col_{i}": c for i, c in enumerate(cells)})

            if rows:
                tables.append(rows)

        return tables

    @staticmethod
    def _extract_lists(soup: BeautifulSoup) -> list[list[str]]:
        """Extract meaningful lists from the page."""
        result = []
        for ul in soup.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li", recursive=False)]
            # Only include lists with 3+ items (likely data, not nav)
            if len(items) >= 3:
                result.append(items)
        return result

    @staticmethod
    def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract absolute links from the page."""
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if isinstance(href, list):
                href = href[0]
            abs_url = urljoin(base_url, href)
            if abs_url.startswith("http") and abs_url not in links:
                links.append(abs_url)
        return links

    @staticmethod
    def _extract_meta(soup: BeautifulSoup) -> dict[str, str]:
        """Extract meta tags from the page."""
        meta: dict[str, str] = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property") or ""
            content = tag.get("content", "")
            if isinstance(name, str) and isinstance(content, str) and name and content:
                meta[name] = content
        return meta
