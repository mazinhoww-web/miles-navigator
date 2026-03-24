"""
Scraper Melhores Destinos — blog de milhas com análises de CPM.
DIFERENCIAL: também extrai valores-alvo de VPP publicados em posts de análise.
"""
import re
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from miles_radar.logger import logger

# Padrões para extrair valores-alvo VPP do Melhores Destinos
VPP_PATTERNS = [
    r'valor[- ]alvo[^\d]*R?\$?\s*([\d,\.]+)\s*(?:o?\s*milh[eê]iro|/\s*1\.?000)',
    r'CPM[^\d]*R?\$?\s*([\d,\.]+)\s*(?:é|é um|seria)',
    r'bom negócio[^\d]*R?\$?\s*([\d,\.]+)',
    r'R?\$?\s*([\d,\.]+)\s*(?:o?\s*milh[eê]iro|por\s+1\.?000\s+milhas)',
]

PROMO_KW = ["bônus", "bonus", "transferência", "transferencia", "milhas",
            "pontos", "smiles", "latam", "azul", "livelo", "esfera",
            "promoção", "promocao", "milheiro", "cpm", "valor-alvo"]

class MelhoresDestinosScraper(BaseScraper):
    name = "melhoresdestinos"
    base_url = "https://www.melhoresdestinos.com.br"
    interval_minutes = 15

    URLS = [
        "https://www.melhoresdestinos.com.br/milhas/",
        "https://www.melhoresdestinos.com.br/milhas/?cat=promos",
        "https://www.melhoresdestinos.com.br/milhas/?cat=transferencia",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items = []
        seen = set()
        for url in self.URLS:
            try:
                html = await self.fetch_with_retry(url)
                for item in self._parse_listing(html, url):
                    if item.url not in seen:
                        seen.add(item.url)
                        items.append(item)
                await self._jitter_sleep(2.0)
            except Exception as e:
                logger.warning(f"[MD] Erro em {url}: {e}")
        logger.info(f"[MD] {len(items)} itens encontrados")
        return items

    def _parse_listing(self, html: str, source_url: str) -> List[ScrapedItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for article in soup.find_all("article")[:25]:
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

                # Extrai referência VPP se presente
                vpp_ref = self._extract_vpp_reference(raw)
                if vpp_ref:
                    raw += f"\nVPP_REF:{vpp_ref['program']}:{vpp_ref['value']}"

                pub = None
                dt_tag = article.find("time")
                if dt_tag and dt_tag.get("datetime"):
                    try:
                        pub = datetime.fromisoformat(dt_tag["datetime"].replace("Z","+00:00"))
                    except Exception:
                        pass

                items.append(ScrapedItem(
                    title=title, url=url, source_name=self.name,
                    raw_text=raw, published_at=pub,
                    extra={"vpp_ref": vpp_ref},
                ))
            except Exception:
                continue
        return items

    def _extract_vpp_reference(self, text: str) -> Optional[dict]:
        """
        Extrai referência de valor-alvo VPP do texto.
        Retorna dict com program e value (R$/1k) se encontrado.
        """
        t = text.lower()
        program = None
        if "smiles" in t:
            program = "Smiles"
        elif "latam" in t:
            program = "LATAM Pass"
        elif "azul" in t:
            program = "Azul Fidelidade"
        if not program:
            return None

        for pattern in VPP_PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                try:
                    val_str = m.group(1).replace(",",".")
                    val = float(val_str)
                    if 8 <= val <= 50:  # range razoável para CPM em BRL
                        return {"program": program, "value": val}
                except Exception:
                    continue
        return None

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        try:
            html = await self.fetch_with_retry(page_url)
            return self._parse_listing(html, page_url)
        except Exception as e:
            logger.warning(f"[MD Bootstrap] {e}")
            return []
