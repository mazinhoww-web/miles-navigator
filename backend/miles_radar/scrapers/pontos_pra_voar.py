"""
Scraper Pontos pra Voar — blog independente de fidelidade.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

PROMO_KW = ["bônus","bonus","transferência","transferencia","milhas","pontos",
            "smiles","pass","azul","livelo","esfera","promoção","promocao"]

class PontosPraVoarScraper(BaseScraper):
    name = "pontospravoar"
    base_url = "https://pontospravoar.com"
    interval_minutes = 30

    URLS = [
        "https://pontospravoar.com/",
        "https://pontospravoar.com/category/pontos-e-milhas/",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        seen = set()
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                for item in self._parse(html, url):
                    if item.url not in seen:
                        seen.add(item.url)
                        items.append(item)
                await self._jitter_sleep(2.0)
            except Exception as e:
                logger.warning(f"[PPV] Erro em {url}: {e}")
        logger.info(f"[PPV] {len(items)} itens encontrados")
        return items

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        for article in soup.find_all("article")[:20]:
            try:
                link = article.find("a", href=True)
                title_tag = article.find(["h1","h2","h3"])
                if not link or not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                if not any(kw in title.lower() for kw in PROMO_KW):
                    continue
                url = link["href"]
                if not url.startswith("http"):
                    url = self.base_url + url
                excerpt = article.find("p")
                raw = f"{title}\n{excerpt.get_text(strip=True) if excerpt else ''}"
                pub = None
                dt_tag = article.find("time")
                if dt_tag and dt_tag.get("datetime"):
                    try: pub = datetime.fromisoformat(dt_tag["datetime"].replace("Z","+00:00"))
                    except Exception: pass
                items.append(ScrapedItem(title=title, url=url, source_name=self.name,
                                         raw_text=raw, published_at=pub))
            except Exception:
                continue
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse(html, page_url)
        except Exception as e:
            logger.warning(f"[PPV Bootstrap] {e}")
            return []
