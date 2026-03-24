"""
Scraper Livelo — maior agregador de pontos do Brasil.
Cobre: página de transferências bonificadas + blog de promoções.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

PROMO_KW = ["bônus", "bonus", "transferência", "transferencia", "milhas",
            "latam", "smiles", "azul", "pontos", "oferta"]

class LiveloScraper(BaseScraper):
    name = "livelo"
    base_url = "https://www.livelo.com.br"
    interval_minutes = 60

    URLS = [
        "https://www.livelo.com.br/ganhar-pontos/transferencia-de-pontos",
        "https://www.livelo.com.br/vantagens/blogs/categoria/promocoes",
        "https://www.livelo.com.br/compra-de-pontos",
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
                await self._jitter_sleep(3.0)
            except Exception as e:
                logger.warning(f"[Livelo] Erro em {url}: {e}")
        logger.info(f"[Livelo] {len(items)} itens encontrados")
        return items

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Busca artigos/cards de promoção
        for article in soup.find_all(["article", "div"], class_=re.compile(r"card|post|promo|oferta|blog", re.I))[:20]:
            try:
                link = article.find("a", href=True)
                title_tag = article.find(["h1","h2","h3","h4"])
                if not link or not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = self.base_url + url
                if not any(kw in title.lower() for kw in PROMO_KW):
                    continue
                excerpt = article.find("p")
                raw = f"{title}\n{excerpt.get_text(strip=True) if excerpt else ''}"
                date_tag = article.find("time")
                pub = None
                if date_tag and date_tag.get("datetime"):
                    try:
                        pub = datetime.fromisoformat(date_tag["datetime"].replace("Z","+00:00"))
                    except Exception:
                        pass
                items.append(ScrapedItem(title=title, url=url, source_name=self.name,
                                         raw_text=raw, published_at=pub,
                                         extra={"program_type": "aggregator"}))
            except Exception:
                continue

        # Fallback: extrai blocos de texto com % de bônus
        if len(items) < 3:
            text = soup.get_text(separator="\n", strip=True)
            blocks = re.findall(r'[^\n]*\d+%[^\n]*(?:b[oô]nus|transferência|milhas)[^\n]*', text, re.I)
            for block in blocks[:5]:
                if len(block) > 20:
                    items.append(ScrapedItem(
                        title=f"Livelo — {block[:200]}",
                        url=source_url,
                        source_name=self.name,
                        raw_text=block,
                        published_at=datetime.utcnow(),
                        extra={"program_type": "aggregator"},
                    ))
        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse(html, page_url)
        except Exception as e:
            logger.warning(f"[Livelo Bootstrap] {e}")
            return []
