"""Scraper Sicoob Pontos — cooperativa de crédito."""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class SicoobScraper(BaseScraper):
    name = "sicoob"
    base_url = "https://www.sicoob.com.br"
    interval_minutes = 240
    URLS = ["https://www.sicoob.com.br/web/sicoob/cartoes", "https://blog.sicoob.com.br/milhas/"]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(5.0)
            except Exception as e:
                logger.warning(f"[Sicoob] {url}: {e}")
        logger.info(f"[Sicoob] {len(items)} itens")
        return items

    def _parse(self, html: str, su: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        text = soup.get_text(separator="\n", strip=True)
        blocks = re.findall(r'[^\n]*(?:b[oô]nus|transferência|milhas|pontos)[^\n]*\d+%[^\n]*|[^\n]*\d+%[^\n]*(?:b[oô]nus|milhas)[^\n]*', text, re.I)
        for b in blocks[:3]:
            if len(b) > 15:
                items.append(ScrapedItem(title=f"Sicoob — {b[:200]}", url=su,
                    source_name=self.name, raw_text=b, published_at=datetime.utcnow(),
                    extra={"bank": "Sicoob", "origin": "Sicoob"}))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try: html = await self.fetch_with_retry(page_url); return self._parse(html, page_url)
        except Exception as e: logger.warning(f"[Sicoob Bootstrap] {e}"); return []
