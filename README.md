# Miles Navigator

Monitor de campanhas de milhas do mercado brasileiro — frontend React + backend FastAPI + scraping via Apify.

## Estrutura do repositório

```
miles-navigator/
  src/                  ← Frontend React (Vite + TypeScript)
  backend/              ← API FastAPI + scrapers + scheduler
  supabase/             ← Edge Functions + migrations (Apify config panel)
  public/
  .env                  ← Variáveis do frontend (VITE_*)
```

---

## Setup local — desenvolvimento

### Pré-requisitos
- Node.js 20+ ou Bun
- Python 3.12+
- Docker + Docker Compose
- Conta Supabase (já configurada — ver `.env`)

### 1. Frontend

```bash
# Instalar dependências
npm install

# Rodar em dev (proxy automático para http://localhost:8000)
npm run dev
```

O frontend estará em **http://localhost:5173**.

### 2. Backend

```bash
cd backend

# Copiar e preencher variáveis
cp .env.example .env
# Editar .env com suas credenciais

# Subir PostgreSQL + Evolution API via Docker
docker-compose up -d db evolution

# Instalar dependências Python
pip install -r requirements.txt

# Rodar migrações
alembic upgrade head

# Subir a API
uvicorn miles_radar.main:app --reload --port 8000
```

A API estará em **http://localhost:8000** e o `VITE_API_URL` no `.env` já aponta para lá.

### 3. Backend completo via Docker

```bash
cd backend
cp .env.example .env
# Editar .env

docker-compose up -d
```

Isso sobe: API + PostgreSQL + Evolution API.

---

## Configuração do Apify

O scraping de campanhas é feito via [Apify](https://apify.com) — sem Playwright local.

### 1. Criar conta Apify e gerar token

Acesse **https://console.apify.com/account/integrations** e copie o API token.

### 2. Configurar token no Supabase (Edge Function)

```bash
# Via Supabase CLI
supabase secrets set APIFY_API_TOKEN=apify_api_xxxx

# Ou via painel: supabase.com → projeto → Edge Functions → Secrets
```

### 3. Configurar no backend `.env`

```env
APIFY_TOKEN=apify_api_xxxx
```

### 4. Configurar Actor IDs no painel

Acesse **http://localhost:5173/apify** e configure o Actor ID de cada fonte.

**Blogs WordPress** (passageirodeprimeira, melhoresdestinos, mestredasmilhas, pontospravoar):
→ Use `apify/website-content-crawler` — zero configuração, extrai texto limpo automaticamente.

**Programas oficiais** (smiles, latampass, azul, livelo, esfera):
→ Use `apify/playwright-scraper` com proxy residencial rotacionado.

**Bancos** (itau, nubank, c6, inter, sicoob):
→ Requerem proxy residencial + retry agressivo. Configuração avançada.

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/health` | Status do sistema e scrapers |
| GET | `/api/promos` | Lista de campanhas com filtros |
| GET | `/api/promos/active` | Campanhas ativas agora |
| GET | `/api/promos/{id}` | Detalhe de campanha |
| GET | `/api/analysis/month` | KPIs e série temporal do mês |
| GET | `/api/history` | Histórico por rota e janela |
| GET | `/api/history/seasonality` | Heatmap de sazonalidade |
| GET | `/api/history/insights` | Insights automáticos |
| GET | `/api/vpp` | VPP por programa e janela |
| GET | `/api/vpp/all` | VPP de todos os programas |
| GET | `/api/vpp/campaign/{id}` | VPP por tier de uma campanha |
| GET | `/api/predictions/all` | Previsões para todas as rotas |
| GET | `/api/predictions/events` | Calendário de eventos recorrentes |
| GET | `/api/watchlist` | Lista de entradas na watchlist |
| POST | `/api/watchlist` | Adicionar à watchlist |
| DELETE | `/api/watchlist/{id}` | Remover da watchlist |
| POST | `/api/scrape/trigger` | Disparar scraping manual |

---

## Valores de referência VPP (Melhores Destinos, dez/2025)

| Programa | Valor-alvo (R$/1k milhas) |
|----------|--------------------------|
| Smiles | R$16,00 |
| LATAM Pass | R$25,00 |
| Azul Fidelidade | R$14,00 |

**Fórmula VPP Real:** `VPP = CPM_origem × paridade ÷ (1 + bonus_pct/100)`

---

## Deploy

### Frontend (Vercel/Netlify)

```bash
npm run build
# dist/ → deploy
```

Definir variável de ambiente:
```
VITE_API_URL=https://seu-backend.com
```

### Backend (VPS/Railway/Render)

```bash
cd backend
docker-compose -f docker-compose.yml up -d
```

---

## Fase 6 — Parser LLM (pendente)

O backend inclui `miles_radar/parsers/llm_parser.py` que usa `claude-sonnet-4-20250514` para extrair campos estruturados de posts ambíguos (confidence < 0.7). Para ativar:

```env
ANTHROPIC_API_KEY=sk-ant-xxxx
LLM_ENABLED=true
```
