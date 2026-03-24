"""Scraper Azul Fidelidade (TudoAzul) - com loyalty tiers reais."""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

class AzulScraper(BaseScraper):
    name = "azul"
    base_url = "https://www.tudoazul.com.br"
    interval_minutes = 30
    URLS = ["https://www.tudoazul.com.br/promocoes", "https://www.tudoazul.com.br/ganhar-pontos"]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                items.extend(self._parse(html, url))
                await self._jitter_sleep(3.0)
            except Exception as e:
                logger.warning(f"[Azul] Erro em {url}: {e}")
        logger.info(f"[Azul] {len(items)} itens encontrados")
        return items

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        links = soup.find_all("a", href=re.compile(r"/promo|/oferta|/transferencia|/compra", re.I))
        page_text = soup.get_text(separator="\n", strip=True)
        bonus_blocks = re.findall(r'[^\n]*(?:\d+%[^\n]*b[oô]nus|b[oô]nus[^\n]*\d+%)[^\n]*', page_text, re.I)
        for block in bonus_blocks[:8]:
            if len(block) > 20:
                # Detecta loyalty tiers do Azul no bloco
                loyalty_info = self._extract_loyalty_info(block)
                items.append(ScrapedItem(
                    title=f"Azul Fidelidade — {block[:200]}",
                    url=source_url,
                    source_name=self.name,
                    raw_text=block + ("\n" + loyalty_info if loyalty_info else ""),
                    published_at=datetime.utcnow(),
                    extra={"program": "Azul Fidelidade", "has_loyalty_tiers": bool(loyalty_info)},
                ))
        return items

    def _extract_loyalty_info(self, text: str) -> str:
        """Detecta os loyalty tiers do Azul no texto."""
        patterns = ["+5%.*?6.*?meses", "+10%.*?1.*?ano", "+20%.*?3.*?anos", "+30%.*?5.*?anos"]
        found = [p for p in patterns if re.search(p, text, re.I)]
        return "; ".join(found) if found else ""

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse(html, page_url)
        except Exception as e:
            logger.warning(f"[Azul Bootstrap] Erro: {e}")
            return []
