"""
ApifyClient — integra com a API REST do Apify para buscar resultados
dos Actors configurados para cada fonte de scraping.

Substitui o Playwright local. Cada fonte tem um Actor ID configurado
no .env. O scheduler sincroniza os datasets periodicamente.

Uso:
    client = ApifyClient()
    items  = await client.sync_source("passageirodeprimeira", settings.APIFY_ACTOR_PASSAGEIRODEPRIMEIRA, since)
"""
import httpx
from typing import List, Optional
from datetime import datetime

from miles_radar.scrapers.base import ScrapedItem
from miles_radar.settings import settings
from miles_radar.logger import logger

APIFY_BASE = "https://api.apify.com/v2"


class ApifyClient:
    def __init__(self):
        self.token = settings.APIFY_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def get_dataset_items(
        self,
        dataset_id: str,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[dict]:
        """Busca itens de um dataset Apify. Filtra por crawledAt se `since` informado."""
        params = {"limit": limit, "clean": "true", "format": "json"}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                headers=self.headers,
                params=params,
            )
            r.raise_for_status()
            items = r.json()

        if since:
            items = [
                i for i in items
                if i.get("crawledAt") and
                datetime.fromisoformat(i["crawledAt"].replace("Z", "+00:00")).replace(tzinfo=None) > since
            ]
        return items

    async def trigger_actor(self, actor_id: str, input_data: dict = None) -> str:
        """Dispara um Actor e retorna o run ID."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{APIFY_BASE}/acts/{actor_id}/runs",
                headers=self.headers,
                json={"input": input_data or {}},
            )
            r.raise_for_status()
            return r.json()["data"]["id"]

    async def get_last_run_dataset(self, actor_id: str) -> Optional[str]:
        """Retorna o dataset ID do último run bem-sucedido de um Actor."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{APIFY_BASE}/acts/{actor_id}/runs/last",
                headers=self.headers,
                params={"status": "SUCCEEDED"},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()["data"]["defaultDatasetId"]

    async def sync_source(
        self,
        source_name: str,
        actor_id: str,
        since: datetime,
    ) -> List[ScrapedItem]:
        """
        Sincroniza uma fonte: pega dataset do último run e converte em ScrapedItems.

        Formato esperado de cada item no dataset Apify:
        {
            "title": "...",
            "url": "...",
            "publishedAt": "2026-03-24T10:00:00Z",  // ISO 8601
            "crawledAt": "2026-03-24T10:05:00Z",
            "bodyText": "Texto limpo do artigo...",
            "bodyHtml": "<p>HTML original...</p>",  // opcional
            "metaDescription": "..."                // opcional
        }
        """
        if not actor_id:
            logger.debug(f"[apify] {source_name}: actor_id não configurado, pulando")
            return []

        dataset_id = await self.get_last_run_dataset(actor_id)
        if not dataset_id:
            logger.warning(f"[apify] Nenhum run SUCCEEDED para {source_name} ({actor_id})")
            return []

        raw_items = await self.get_dataset_items(dataset_id, since=since)
        logger.info(f"[apify] {source_name}: {len(raw_items)} itens novos no dataset")

        scraped = []
        for item in raw_items:
            pub_raw = item.get("publishedAt")
            published_at: Optional[datetime] = None
            if pub_raw:
                try:
                    published_at = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    pass

            scraped.append(ScrapedItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source_name=source_name,
                raw_text=item.get("bodyText", item.get("text", "")),
                published_at=published_at,
                extra={
                    "html": item.get("bodyHtml", ""),
                    "meta_description": item.get("metaDescription", ""),
                },
            ))
        return scraped
