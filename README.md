# ✈️ Miles Navigator

Monitor de inteligência de campanhas de milhas do mercado brasileiro. Detecta promoções em tempo real em 14 fontes, calcula VPP por perfil de cliente e prevê próximas janelas via análise histórica.

---

## Estrutura do repositório

```
miles-navigator/
├── src/                    ← Frontend React (Vite + TypeScript)
│   ├── pages/              ← 8 páginas da aplicação
│   ├── components/         ← UI components + layout
│   ├── lib/api.ts          ← Helper de chamadas à API FastAPI
│   └── lib/apify.ts        ← Integração Apify via Supabase Edge Function
├── supabase/
│   ├── functions/apify-proxy/   ← Edge Function proxy do Apify (token seguro)
│   └── migrations/              ← Schema da tabela apify_actors
└── backend/                ← API FastAPI (Python 3.12)
    ├── miles_radar/        ← Módulos Python
    ├── docker-compose.yml  ← PostgreSQL + API + Evolution
    └── .env.example        ← Template de variáveis de ambiente
```

---

## Páginas

| Rota | Página | Descrição |
|---|---|---|
| `/` | Monitor | Campanhas ativas em tempo real, KPIs do mês, gráfico diário |
| `/analise-mensal` | Análise Mensal | KPIs + distribuição por programa e tipo |
| `/historico` | Histórico | Sazonalidade, série temporal, insights automáticos |
| `/vpp` | VPP | Valor Por Ponto real + simulador interativo |
| `/previsao` | Previsão | Probabilidade P(7/15/30d), calendário de eventos |
| `/watchlist` | Watchlist | Monitoramento personalizado de rotas |
| `/status` | Status | Health dos 14 scrapers + trigger manual |
| `/apify` | Config Apify | Gerencia Actor IDs, dispara runs, acompanha status |

---

## Setup local (desenvolvimento)

### 1. Frontend

```bash
npm install
npm run dev
# → http://localhost:5173
```

Variável obrigatória no `.env`:
```
VITE_API_URL=http://localhost:8000
```

### 2. Backend (Python + Docker)

```bash
cd backend
cp .env.example .env
# Editar DATABASE_URL, ANTHROPIC_API_KEY, APIFY_TOKEN, etc.

docker-compose up -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Supabase

```bash
# Linkar ao projeto
supabase link --project-ref ixgcpvnhzwvdarzydbuv

# Aplicar migration (cria tabela apify_actors + seed 14 sources)
supabase db push

# Deploy da Edge Function
supabase functions deploy apify-proxy

# Configurar token Apify (nunca expor no frontend)
supabase secrets set APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxx
```

---

## Arquitetura Apify

```
Apify Actors (cloud)
      ↓  datasets
Supabase Edge Function (apify-proxy)   ← token seguro no Supabase secrets
      ↓  via supabase.functions.invoke
Frontend /apify                        ← dispara runs, monitora status
      ↓
Backend APScheduler (apify_sync_job)   ← lê datasets → parser → PostgreSQL
```

### Actors recomendados por tipo de fonte

| Tipo | Actor | Custo |
|---|---|---|
| Blogs WordPress | `apify/website-content-crawler` | baixo |
| Sites dinâmicos (Smiles, LATAM, Azul) | `apify/playwright-scraper` | médio |
| Sites com Cloudflare (bancos) | `apify/playwright-scraper` + proxy residencial | alto |

**Para começar agora** — configure estes 4 (zero config extra):
```
passageirodeprimeira  → apify/website-content-crawler
melhoresdestinos      → apify/website-content-crawler
mestredasmilhas       → apify/website-content-crawler
pontospravoar         → apify/website-content-crawler
```

---

## API FastAPI — endpoints principais

```
GET  /api/health                    Status dos 14 scrapers
GET  /api/promos                    Lista campanhas (filtros query)
GET  /api/promos/active             Campanhas ativas agora
GET  /api/promos/:id                Detalhe + tiers de bônus
GET  /api/analysis/month            KPIs e série temporal do mês
GET  /api/history                   Histórico por rota (3–36 meses)
GET  /api/history/seasonality       Heatmap sazonalidade
GET  /api/history/insights          Insights automáticos
GET  /api/vpp                       VPP histórico por programa
GET  /api/vpp/all                   VPP todos os programas
GET  /api/vpp/campaign/:id          VPP por tier de uma campanha
GET  /api/predictions/all           Previsão todas as rotas
GET  /api/predictions/events        Calendário de eventos recorrentes
POST /api/watchlist                 Adicionar rota à watchlist
POST /api/scrape/trigger            Disparar scraping manual
```

---

## Deploy em produção

1. Deploy do backend em VPS/container (Railway, Fly.io, Render)
2. Atualizar `VITE_API_URL` no Lovable → Settings → Environment Variables
3. Rebuild do frontend no Lovable
4. `supabase secrets set APIFY_API_TOKEN=...`

---

## Stack

**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · shadcn/ui · TanStack Query · Recharts · Framer Motion
**Backend:** Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · APScheduler
**Infra:** Supabase (config + Edge Function) · Apify Cloud (scraping) · Docker Compose
**WhatsApp:** Evolution API
