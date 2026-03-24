"""
Scraper do Passageiro de Primeira (passageirodeprimeira.com)
Maior portal de milhas do Brasil — cobre praticamente todas as promoções.
"""
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger


PROMO_KEYWORDS = [
    "transferência", "transferencia", "bônus", "bonus",
    "smiles", "pass", "azul fidelidade", "tudoazul",
    "livelo", "esfera", "milhas", "pontos", "compra",
    "flash", "hoje", "promoção", "promocao"
]


class PassageiroDePrimeiraScraper(BaseScraper):
    name = "passageirodeprimeira"
    base_url = "https://passageirodeprimeira.com"
    interval_minutes = 15

    # Categorias com maior densidade de promoções
    PROMO_CATEGORIES = [
        "/categorias/smiles/",
        "/categorias/pass/",
        "/categorias/azul-fidelidade/",
        "/categorias/livelo/",
        "/categorias/esfera/",
        "/categorias/promocoes/",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        seen_urls = set()

        for category_path in self.PROMO_CATEGORIES:
            url = f"{self.base_url}{category_path}"
            try:
                logger.debug(f"[PP] Buscando: {url}")
                html = await self.fetch_with_retry(url)
                page_items = self._parse_listing(html, url)

                for item in page_items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        items.append(item)

                await self._jitter_sleep(2.0)

            except Exception as e:
                logger.warning(f"[PP] Erro em {url}: {e}")
                continue

        logger.info(f"[PP] {len(items)} itens encontrados no total")
        return items

    def _parse_listing(self, html: str, source_url: str) -> List[ScrapedItem]:
        """Extrai posts da página de listagem."""
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Posts do PP usam article tags ou divs com classes específicas
        articles = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"post|entry|article"))

        for article in articles[:20]:  # Máximo 20 por página
            try:
                # Título e URL
                link_tag = article.find("a", href=True)
                title_tag = article.find(["h1", "h2", "h3"])

                if not link_tag or not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                url = link_tag["href"]
                if not url.startswith("http"):
                    url = f"{self.base_url}{url}"

                # Filtra só posts de promoções de milhas
                title_lower = title.lower()
                if not any(kw in title_lower for kw in PROMO_KEYWORDS):
                    continue

                # Texto do excerpt
                excerpt_tag = article.find("p") or article.find(class_=re.compile(r"excerpt|summary|description"))
                raw_text = f"{title}\n{excerpt_tag.get_text(strip=True) if excerpt_tag else ''}"

                # Data de publicação
                date_tag = article.find("time")
                published_at = None
                if date_tag and date_tag.get("datetime"):
                    try:
                        published_at = datetime.fromisoformat(
                            date_tag["datetime"].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                items.append(ScrapedItem(
                    title=title,
                    url=url,
                    source_name=self.name,
                    raw_text=raw_text,
                    published_at=published_at,
                ))

            except Exception as e:
                logger.debug(f"[PP] Erro ao parsear artigo: {e}")
                continue

        return items

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        """Busca uma página específica do arquivo (para bootstrap histórico)."""
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse_listing(html, page_url)
        except Exception as e:
            logger.warning(f"[PP Bootstrap] Erro em {page_url}: {e}")
            return []
