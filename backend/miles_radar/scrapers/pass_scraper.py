"""
Scraper do programa Pass
"""
import os
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger


class PassScraper(BaseScraper):
    name = "pass"
    base_url = os.getenv("PASS_SCRAPER_URL", "")
    interval_minutes = 30

    PROMO_URLS = [
        os.getenv("PASS_SCRAPER_URL", "") + "/pt_br/promocoes",
        os.getenv("PASS_SCRAPER_URL", "") + "/pt_br/ganhar-pontos/transferencia-de-pontos",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []

        for url in self.PROMO_URLS:
            try:
                logger.debug(f"[Pass] Buscando: {url}")
                html = await self.fetch_with_retry(url, wait_for="body")
                page_items = self._parse_pass(html, url)
                items.extend(page_items)
                await self._jitter_sleep(3.0)
            except Exception as e:
                logger.warning(f"[Pass] Erro em {url}: {e}")

        logger.info(f"[Pass] {len(items)} promoções encontradas")
        return items

    def _parse_pass(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Busca links de promoções
        promo_links = soup.find_all("a", href=re.compile(r"/promocoes|/ganhar|/transferencia", re.I))

        for link in promo_links[:25]:
            try:
                href = link.get("href", "")
                if not href or href == source_url:
                    continue

                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                title = link.get_text(strip=True) or link.get("title", "") or link.get("aria-label", "")

                if not title or len(title) < 5:
                    continue

                items.append(ScrapedItem(
                    title=f"Pass — {title}",
                    url=full_url,
                    source_name=self.name,
                    raw_text=title,
                    published_at=None,
                    extra={"program": "Pass"},
                ))
            except Exception:
                continue

        # Fallback: texto da página
        if len(items) < 2:
            page_text = soup.get_text(separator="\n", strip=True)
            bonus_blocks = re.findall(r'[^\n]*\d+%[^\n]*', page_text, re.I)
            pass_blocks = [b for b in bonus_blocks if any(
                kw in b.lower() for kw in ["bônus", "bonus", "pontos", "transferência", "livelo", "itaú"]
            )]
            for block in pass_blocks[:5]:
                if len(block) > 20:
                    items.append(ScrapedItem(
                        title=f"Pass — {block[:200]}",
                        url=source_url,
                        source_name=self.name,
                        raw_text=block,
                        published_at=datetime.utcnow(),
                        extra={"program": "Pass"},
                    ))

        return items
