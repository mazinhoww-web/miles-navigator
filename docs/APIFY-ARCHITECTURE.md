# Miles Radar — Arquitetura Apify
# Substituição dos scrapers Playwright por Apify Actors

---

## Por que Apify?

Os scrapers atuais (Playwright) rodam localmente no mesmo container da API. Isso cria:
- Consumo alto de RAM (Playwright ~500MB por browser headless)
- Risco de bloqueio por IP único
- Manutenção de chromium no Docker
- Scrapers como azul/livelo/bancos bloqueiam IPs repetidos

**Com Apify:**
- Cada fonte = 1 Actor isolado na nuvem Apify
- Pool de proxies rotacionados incluído
- Retry automático, browser fingerprinting
- Resultados ficam em Datasets — a API puxa quando quiser
- Custo estimado: ~$30/mês para 14 fontes × 6h interval

---

## Arquitetura geral

```
┌─────────────────────────────────────────────┐
│                   APScheduler               │
│  job: "apify_sync" a cada 30min             │
└──────────────────┬──────────────────────────┘
                   │ chama
┌──────────────────▼──────────────────────────┐
│          ApifyClient (HTTP REST)             │
│  1. GET /v2/actor-runs (runs recentes)       │
│  2. GET /v2/datasets/:id/items               │
└──────────────────┬──────────────────────────┘
                   │ retorna ScrapedItems
┌──────────────────▼──────────────────────────┐
│         CampaignParser (já existe)           │
│  → LLMParser se confidence < 0.7             │
│  → Deduplication via SHA-256                 │
│  → Salva em PostgreSQL                       │
└─────────────────────────────────────────────┘
```

---

## Estrutura do novo módulo `miles_radar/scrapers/apify_client.py`

```python
"""
ApifyClient — integra com a API REST do Apify para buscar resultados
dos Actors configurados para cada fonte de scraping.

Substitui o Playwright local. Cada fonte tem um Actor ID configurado
no .env. O scheduler sincroniza os datasets periodicamente.
"""
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
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
        limit: int = 200
    ) -> List[dict]:
        """Busca itens de um dataset Apify. Filtra por data se `since` informado."""
        params = {"limit": limit, "clean": "true", "format": "json"}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                headers=self.headers,
                params=params
            )
            r.raise_for_status()
            items = r.json()
        
        if since:
            items = [
                i for i in items
                if i.get("crawledAt") and 
                datetime.fromisoformat(i["crawledAt"].replace("Z","")) > since
            ]
        return items

    async def trigger_actor(self, actor_id: str, input_data: dict = None) -> str:
        """Dispara um Actor e retorna o run ID."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{APIFY_BASE}/acts/{actor_id}/runs",
                headers=self.headers,
                json={"input": input_data or {}}
            )
            r.raise_for_status()
            return r.json()["data"]["id"]

    async def get_last_run_dataset(self, actor_id: str) -> Optional[str]:
        """Retorna o dataset ID do último run bem-sucedido de um Actor."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{APIFY_BASE}/acts/{actor_id}/runs/last",
                headers=self.headers,
                params={"status": "SUCCEEDED"}
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()["data"]["defaultDatasetId"]

    async def sync_source(self, source_name: str, actor_id: str, since: datetime) -> List[ScrapedItem]:
        """
        Sincroniza uma fonte: pega dataset do último run e converte em ScrapedItems.
        """
        dataset_id = await self.get_last_run_dataset(actor_id)
        if not dataset_id:
            logger.warning(f"[apify] Nenhum run completo para {source_name}")
            return []
        
        raw_items = await self.get_dataset_items(dataset_id, since=since)
        logger.info(f"[apify] {source_name}: {len(raw_items)} itens no dataset")
        
        scraped = []
        for item in raw_items:
            # Formato esperado do Actor Apify (ver seção "Formato do output")
            scraped.append(ScrapedItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source_name=source_name,
                raw_text=item.get("bodyText", item.get("text", "")),
                published_at=datetime.fromisoformat(item["publishedAt"].replace("Z",""))
                             if item.get("publishedAt") else None,
                extra={
                    "html": item.get("bodyHtml", ""),
                    "meta_description": item.get("metaDescription", ""),
                }
            ))
        return scraped
```

---

## Configuração dos Actors no .env

Adicionar ao `.env.example`:

```env
# Apify
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxx

# Actor IDs — configurar após criar os actors no Apify
APIFY_ACTOR_PASSAGEIRODEPRIMEIRA=username/passageiro-de-primeira
APIFY_ACTOR_MELHORESDESTINOS=username/melhores-destinos
APIFY_ACTOR_MESTREDASMILHAS=username/mestre-das-milhas
APIFY_ACTOR_PONTOSPRAVOAR=username/pontos-pra-voar
APIFY_ACTOR_SMILES=username/smiles-promo
APIFY_ACTOR_FIDELIDADE=username/fidelidade-promo
APIFY_ACTOR_AZUL=username/tudo-azul-promo
APIFY_ACTOR_LIVELO=username/livelo-transferencia
APIFY_ACTOR_ESFERA=username/esfera-promo
APIFY_ACTOR_ITAU_IUPP=username/itau-iupp
APIFY_ACTOR_NUBANK=username/nubank-rewards
APIFY_ACTOR_C6=username/c6-atomos
APIFY_ACTOR_INTER=username/inter-loop
APIFY_ACTOR_SICOOB=username/sicoob-pontos
```

---

## Formato de output obrigatório dos Actors Apify

Cada Actor deve salvar no dataset itens neste formato:

```json
{
  "title": "Livelo transfere com até 80% de bônus para programa parceiro",
  "url": "https://www.passageirodeprimeira.com/livelo-parceiro-80-bonus",
  "publishedAt": "2026-03-24T10:00:00Z",
  "crawledAt": "2026-03-24T10:05:00Z",
  "bodyText": "Texto limpo do artigo sem HTML...",
  "bodyHtml": "<p>HTML original se necessário...</p>",
  "metaDescription": "Meta description da página"
}
```

---

## Actors pré-prontos no Apify Store (usar ao máximo)

Para blogs WordPress (passageirodeprimeira, melhoresdestinos, mestredasmilhas, pontospravoar):
→ **Actor: `apify/web-scraper`** ou **`apify/cheerio-scraper`** configurado com:
  - Start URL: URL da categoria de promoções do blog
  - Link selector: `a[href*="/milhas"], a[href*="/promo"], a[href*="/bonus"]`
  - Page function: extrai title, url, publishedAt, bodyText

Para sites dinâmicos (Smiles, Azul, Livelo, Esfera):
→ **Actor: `apify/playwright-scraper`** com proxy residencial rotacionado.

**Dica:** Usar o Actor `apify/website-content-crawler` para blogs estáticos — zero configuração, extrai texto limpo automaticamente.

---

## Novo job no Scheduler (substitui jobs individuais por fonte)

```python
# miles_radar/scheduler/jobs.py — adicionar este job

async def apify_sync_job():
    """
    Job centralizado que sincroniza todas as 14 fontes via Apify.
    Roda a cada 30 minutos. Substitui os 14 jobs Playwright individuais.
    """
    from miles_radar.scrapers.apify_client import ApifyClient
    from miles_radar.parsers.campaign_parser import CampaignParser
    from miles_radar.models.database import SessionLocal
    
    client = ApifyClient()
    parser = CampaignParser()
    since = datetime.utcnow() - timedelta(hours=1)  # últimos 60min
    
    ACTOR_MAP = {
        "passageirodeprimeira": settings.APIFY_ACTOR_PASSAGEIRODEPRIMEIRA,
        "melhoresdestinos":     settings.APIFY_ACTOR_MELHORESDESTINOS,
        "mestredasmilhas":      settings.APIFY_ACTOR_MESTREDASMILHAS,
        "pontospravoar":        settings.APIFY_ACTOR_PONTOSPRAVOAR,
        "smiles":               settings.APIFY_ACTOR_SMILES,
        "fidelidade":           settings.APIFY_ACTOR_FIDELIDADE,
        "azul":                 settings.APIFY_ACTOR_AZUL,
        "livelo":               settings.APIFY_ACTOR_LIVELO,
        "esfera":               settings.APIFY_ACTOR_ESFERA,
        "itau_iupp":            settings.APIFY_ACTOR_ITAU_IUPP,
        "nubank":               settings.APIFY_ACTOR_NUBANK,
        "c6":                   settings.APIFY_ACTOR_C6,
        "inter":                settings.APIFY_ACTOR_INTER,
        "sicoob":               settings.APIFY_ACTOR_SICOOB,
    }
    
    db = SessionLocal()
    total_new = 0
    try:
        for source_name, actor_id in ACTOR_MAP.items():
            if not actor_id:
                continue
            try:
                items = await client.sync_source(source_name, actor_id, since)
                for item in items:
                    campaign = parser.parse(item)
                    if campaign:
                        saved = _save_if_new(db, campaign)
                        if saved:
                            total_new += 1
            except Exception as e:
                logger.error(f"[apify_sync] Erro em {source_name}: {e}")
    finally:
        db.close()
    
    logger.info(f"[apify_sync] Sincronização completa. {total_new} campanhas novas.")
```

---

## Registro no APScheduler

```python
# Em jobs.py, substituir os 14 jobs individuais por:
scheduler.add_job(
    apify_sync_job,
    trigger="interval",
    minutes=30,
    id="apify_sync",
    max_instances=1,
    name="Apify Sync — todas as fontes",
)
```

---

## Adicionar ao settings.py

```python
class Settings(BaseSettings):
    # ... campos existentes ...
    
    # Apify
    APIFY_TOKEN: str = ""
    APIFY_ACTOR_PASSAGEIRODEPRIMEIRA: str = ""
    APIFY_ACTOR_MELHORESDESTINOS: str = ""
    APIFY_ACTOR_MESTREDASMILHAS: str = ""
    APIFY_ACTOR_PONTOSPRAVOAR: str = ""
    APIFY_ACTOR_SMILES: str = ""
    APIFY_ACTOR_FIDELIDADE: str = ""
    APIFY_ACTOR_AZUL: str = ""
    APIFY_ACTOR_LIVELO: str = ""
    APIFY_ACTOR_ESFERA: str = ""
    APIFY_ACTOR_ITAU_IUPP: str = ""
    APIFY_ACTOR_NUBANK: str = ""
    APIFY_ACTOR_C6: str = ""
    APIFY_ACTOR_INTER: str = ""
    APIFY_ACTOR_SICOOB: str = ""
```

---

## Adicionar ao requirements.txt

```
httpx>=0.27.0       # já deve existir; usado pelo LLMParser
# remover playwright se não mais necessário
```

---

## Plano de migração (sem downtime)

### Fase A — Paralelo (semana 1)
1. Criar conta Apify + gerar token
2. Configurar 3 actors mais simples: passageirodeprimeira, melhoresdestinos, pontospravoar (blogs WordPress puros)
3. Usar `apify/website-content-crawler` para os 3 — zero código de scraping
4. Testar `ApifyClient.sync_source()` manualmente
5. Rodar `apify_sync_job` em paralelo com scrapers Playwright

### Fase B — Substituição (semana 2)
1. Confirmar que dados chegam corretamente via Apify
2. Desativar scrapers Playwright dos 3 fontes migradas
3. Migrar fontes oficiais: smiles, fidelidade, azul (precisam de actor com proxy)
4. Migrar agregadores: livelo, esfera
5. Migrar bancos: itau_iupp, nubank, c6, inter, sicoob

### Fase C — Cleanup (semana 3)
1. Remover Playwright do requirements.txt
2. Remover chromium do Dockerfile
3. Reduzir RAM do container de 2GB → 512MB
4. Atualizar /api/health para mostrar status dos Actors Apify

---

## Redução de custo — dicas

1. **Blogs WordPress**: usar `apify/cheerio-scraper` (não precisa de browser, 10x mais barato que Playwright)
2. **Schedule no Apify**: configurar os actors para rodar automaticamente no Apify a cada hora → API só lê datasets, não dispara runs
3. **Dataset retention**: Apify retém datasets por 7 dias no plano gratuito — sync a cada 4h é suficiente para blogs

---

## Workflow após Lovable gerar o GitHub

```bash
# 1. Clonar o repo gerado pelo Lovable
git clone https://github.com/seu-usuario/miles-radar-frontend

# 2. Entrar no diretório
cd miles-radar-frontend

# 3. Copiar os arquivos do backend para um subdiretório
mkdir backend
cp -r /path/to/miles-radar-app/* backend/

# 4. Criar .env no frontend
echo "VITE_API_URL=http://localhost:8000" > .env

# 5. Instalar dependências
npm install

# 6. Rodar backend em paralelo
cd backend && docker-compose up -d

# 7. Rodar frontend
npm run dev
```
