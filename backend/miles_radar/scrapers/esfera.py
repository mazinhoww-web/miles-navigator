"""
Scraper Esfera (Santander) — agregador de pontos do Banco Santander.
Campanhas geralmente curtas, frequentemente flash.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class EsferaScraper(BaseScraper):
    name = "esfera"
    base_url = "https://www.esfera.com.vc"
    interval_minutes = 60

    URLS = [
        "https://www.esfera.com.vc/transferir-pontos",
        "https://www.esfera.com.vc/promocoes",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(3.5)
            except Exception as e:
                logger.warning(f"[Esfera] Erro em {url}: {e}")
        logger.info(f"[Esfera] {len(items)} itens encontrados")
        return items

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Links com texto de promoção
        for link in soup.find_all("a", href=True)[:40]:
            text = link.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            t = text.lower()
            if not any(kw in t for kw in ["bônus","bonus","transferência","milhas","pontos","oferta"]):
                continue
            href = link["href"]
            if not href.startswith("http"):
                href = self.base_url + href
            items.append(ScrapedItem(
                title=f"Esfera — {text[:200]}",
                url=href,
                source_name=self.name,
                raw_text=text,
                published_at=datetime.utcnow(),
                extra={"origin": "Esfera", "bank": "Santander"},
            ))

        # Fallback texto bruto
        if len(items) < 2:
            page_text = soup.get_text(separator="\n", strip=True)
            blocks = re.findall(r'[^\n]*\d+%[^\n]*(?:b[oô]nus|transferência)[^\n]*', page_text, re.I)
            for b in blocks[:4]:
                if len(b) > 15:
                    items.append(ScrapedItem(
                        title=f"Esfera — {b[:200]}",
                        url=source_url,
                        source_name=self.name,
                        raw_text=b,
                        published_at=datetime.utcnow(),
                        extra={"origin": "Esfera"},
                    ))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse(html, page_url)
        except Exception as e:
            logger.warning(f"[Esfera Bootstrap] {e}")
            return []
