"""
Scraper do LATAM Pass (latampass.latam.com)
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger


class LatamPassScraper(BaseScraper):
    name = "latampass"
    base_url = "https://latampass.latam.com"
    interval_minutes = 30

    PROMO_URLS = [
        "https://latampass.latam.com/pt_br/promocoes",
        "https://latampass.latam.com/pt_br/ganhar-pontos/transferencia-de-pontos",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []

        for url in self.PROMO_URLS:
            try:
                logger.debug(f"[LATAM] Buscando: {url}")
                html = await self.fetch_with_retry(url, wait_for="body")
                page_items = self._parse_latam(html, url)
                items.extend(page_items)
                await self._jitter_sleep(3.0)
            except Exception as e:
                logger.warning(f"[LATAM] Erro em {url}: {e}")

        logger.info(f"[LATAM] {len(items)} promoções encontradas")
        return items

    def _parse_latam(self, html: str, source_url: str) -> List[ScrapedItem]:
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
                    title=f"LATAM Pass — {title}",
                    url=full_url,
                    source_name=self.name,
                    raw_text=title,
                    published_at=None,
                    extra={"program": "LATAM Pass"},
                ))
            except Exception:
                continue

        # Fallback: texto da página
        if len(items) < 2:
            page_text = soup.get_text(separator="\n", strip=True)
            bonus_blocks = re.findall(r'[^\n]*\d+%[^\n]*', page_text, re.I)
            latam_blocks = [b for b in bonus_blocks if any(
                kw in b.lower() for kw in ["bônus", "bonus", "pontos", "transferência", "livelo", "itaú"]
            )]
            for block in latam_blocks[:5]:
                if len(block) > 20:
                    items.append(ScrapedItem(
                        title=f"LATAM Pass — {block[:200]}",
                        url=source_url,
                        source_name=self.name,
                        raw_text=block,
                        published_at=datetime.utcnow(),
                        extra={"program": "LATAM Pass"},
                    ))

        return items
