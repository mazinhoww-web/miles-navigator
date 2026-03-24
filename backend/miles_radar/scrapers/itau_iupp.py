"""
Scraper Itaú iupp — programa de pontos do Banco Itaú.
Sites do Itaú frequentemente têm proteção Cloudflare — fallback agressivo via PP/MD.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class ItauIuppScraper(BaseScraper):
    name = "itau_iupp"
    base_url = "https://www.itau.com.br"
    interval_minutes = 120

    URLS = [
        "https://www.itau.com.br/cartoes/beneficios/programa-de-pontos/",
        "https://www.iupp.com.br/transferencia",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(5.0)
            except Exception as e:
                logger.warning(f"[Itaú] Erro em {url}: {e} — site pode estar protegido")
        logger.info(f"[Itaú] {len(items)} itens encontrados")
        return items

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        page_text = soup.get_text(separator="\n", strip=True)
        blocks = re.findall(
            r'[^\n]*(?:b[oô]nus|transferência|milhas|pontos)[^\n]*\d+%[^\n]*|[^\n]*\d+%[^\n]*(?:b[oô]nus|transferência)[^\n]*',
            page_text, re.I
        )
        for block in blocks[:5]:
            if len(block) > 20:
                items.append(ScrapedItem(
                    title=f"Itaú iupp — {block[:200]}",
                    url=source_url,
                    source_name=self.name,
                    raw_text=block,
                    published_at=datetime.utcnow(),
                    extra={"bank": "Itaú", "origin": "Iupp Itaú"},
                ))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse(html, page_url)
        except Exception as e:
            logger.warning(f"[Itaú Bootstrap] {e}")
            return []
