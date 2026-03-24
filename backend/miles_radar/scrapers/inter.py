"""Scraper Inter Loop."""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class InterScraper(BaseScraper):
    name = "inter"
    base_url = "https://inter.co"
    interval_minutes = 120
    URLS = ["https://inter.co/inter-loop/", "https://blog.inter.co/categoria/milhas-e-viagens/"]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(4.0)
            except Exception as e:
                logger.warning(f"[Inter] {url}: {e}")
        logger.info(f"[Inter] {len(items)} itens")
        return items

    def _parse(self, html: str, su: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        text = soup.get_text(separator="\n", strip=True)
        blocks = re.findall(r'[^\n]*(?:b[oô]nus|transferência|milhas|loop)[^\n]*\d+%[^\n]*|[^\n]*\d+%[^\n]*(?:b[oô]nus|milhas)[^\n]*', text, re.I)
        for b in blocks[:4]:
            if len(b) > 15:
                items.append(ScrapedItem(title=f"Inter Loop — {b[:200]}", url=su,
                    source_name=self.name, raw_text=b, published_at=datetime.utcnow(),
                    extra={"bank": "Inter", "origin": "Inter Loop"}))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try: html = await self.fetch_with_retry(page_url); return self._parse(html, page_url)
        except Exception as e: logger.warning(f"[Inter Bootstrap] {e}"); return []
