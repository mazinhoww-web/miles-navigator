"""Scraper C6 Átomos."""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class C6Scraper(BaseScraper):
    name = "c6"
    base_url = "https://www.c6bank.com.br"
    interval_minutes = 120
    URLS = ["https://www.c6bank.com.br/atomos/transferir-pontos", "https://www.c6bank.com.br/cartoes/beneficios"]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(4.0)
            except Exception as e:
                logger.warning(f"[C6] {url}: {e}")
        logger.info(f"[C6] {len(items)} itens")
        return items

    def _parse(self, html: str, su: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        text = soup.get_text(separator="\n", strip=True)
        blocks = re.findall(r'[^\n]*(?:b[oô]nus|transferência|milhas|átomos)[^\n]*\d+%[^\n]*|[^\n]*\d+%[^\n]*(?:b[oô]nus|milhas)[^\n]*', text, re.I)
        for b in blocks[:4]:
            if len(b) > 15:
                items.append(ScrapedItem(title=f"C6 Átomos — {b[:200]}", url=su,
                    source_name=self.name, raw_text=b, published_at=datetime.utcnow(),
                    extra={"bank": "C6", "origin": "C6 Átomos"}))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try: html = await self.fetch_with_retry(page_url); return self._parse(html, page_url)
        except Exception as e: logger.warning(f"[C6 Bootstrap] {e}"); return []
