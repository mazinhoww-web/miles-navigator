"""
Scraper do Smiles (smiles.com.br)
Página oficial de promoções do programa da GOL.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger


class SmilesScraper(BaseScraper):
    name = "smiles"
    base_url = "https://www.smiles.com.br"
    interval_minutes = 30

    PROMO_URLS = [
        "https://www.smiles.com.br/portal/promocoes",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []

        for url in self.PROMO_URLS:
            try:
                logger.debug(f"[Smiles] Buscando: {url}")
                html = await self.fetch_with_retry(url, wait_for="body")
                page_items = self._parse_smiles(html, url)
                items.extend(page_items)
                await self._jitter_sleep(3.0)
            except Exception as e:
                logger.warning(f"[Smiles] Erro em {url}: {e}")

        logger.info(f"[Smiles] {len(items)} promoções encontradas")
        return items

    def _parse_smiles(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Smiles usa cards de promoção — busca elementos com textos relevantes
        # O site tem JavaScript, então capturamos o que está no HTML inicial
        promo_blocks = (
            soup.find_all(class_=re.compile(r"promo|card|offer|banner", re.I)) or
            soup.find_all(["article", "section"])
        )

        # Também tenta pegar links diretos de promoções
        all_links = soup.find_all("a", href=re.compile(r"/portal/promocoes|/promocoes/", re.I))

        for link in all_links[:30]:
            try:
                href = link.get("href", "")
                if not href or href == source_url:
                    continue

                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                title = link.get_text(strip=True) or link.get("title", "") or link.get("aria-label", "")

                if not title or len(title) < 5:
                    continue

                title_lower = title.lower()
                promo_keywords = ["bônus", "bonus", "milhas", "transferência", "transferencia", "compra", "clube"]
                if not any(kw in title_lower for kw in promo_keywords):
                    continue

                items.append(ScrapedItem(
                    title=title,
                    url=full_url,
                    source_name=self.name,
                    raw_text=title,
                    published_at=None,
                    extra={"program": "Smiles"},
                ))
            except Exception:
                continue

        # Se encontrou poucos links, captura texto da página toda como fallback
        if len(items) < 3:
            page_text = soup.get_text(separator="\n", strip=True)
            # Extrai blocos com números de bônus
            bonus_blocks = re.findall(r'[^\n]*\d+%[^\n]*bônus[^\n]*|[^\n]*bônus[^\n]*\d+%[^\n]*', page_text, re.I)
            for block in bonus_blocks[:5]:
                if len(block) > 20:
                    items.append(ScrapedItem(
                        title=f"Smiles — {block[:200]}",
                        url=source_url,
                        source_name=self.name,
                        raw_text=block,
                        published_at=datetime.utcnow(),
                        extra={"program": "Smiles"},
                    ))

        return items
