# Miles Radar 🎯

Monitor de campanhas de milhas do mercado brasileiro. Detecta, analisa e alerta sobre
promoções de transferência bonificada — com VPP calculado por perfil, histórico de 36 meses
e previsão preditiva de próximas campanhas.

**14 fontes monitoradas** · **alertas WhatsApp** · **VPP por perfil** · **análise histórica** · **previsão**

---

## Setup em 5 minutos

### Pré-requisitos
- Servidor Linux com Docker + Docker Compose (Ubuntu 22.04 recomendado)
- WhatsApp instalado no celular

### 1. Baixar e extrair

```bash
# Copie o arquivo .tar.gz para o servidor via SCP ou SFTP
tar -xzf miles-radar-fases4-5.tar.gz
cd miles-radar-app
```

### 2. Configurar

```bash
cp .env.example .env
nano .env
```

Edite apenas estas linhas:

```bash
POSTGRES_PASSWORD=SuaSenhaForte2026         # senha do banco (invente uma)
EVOLUTION_API_KEY=minha-chave-secreta-2026  # qualquer texto longo
ALERT_NUMBERS=5565999999999                 # seu WhatsApp: 55 + DDD + número
MIN_BONUS_PCT=40                            # só alerta se bônus >= 40%
```

Salve: `Ctrl+O` → `Enter` → `Ctrl+X`

### 3. Subir o sistema

```bash
docker compose up -d

# Acompanhe os logs
docker compose logs -f app
```

### 4. Conectar o WhatsApp

```bash
# Gera o QR code
curl -X POST "http://localhost:8080/instance/create" \
     -H "apikey: SUA_EVOLUTION_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"instanceName":"milesradar","qrcode":true}'
```

Abra o WhatsApp → Dispositivos conectados → Conectar dispositivo → escaneie o QR code.

### 5. Acessar o dashboard

Abra no navegador: `http://SEU_IP:8000`

---

## Dashboard — telas disponíveis

| Tela | URL | O que mostra |
|------|-----|-------------|
| Monitor | `/` | Campanhas ativas + gráfico do mês + KPIs |
| Análise mensal | `/analise-mensal` | Gantt + heatmap + rankings por mês |
| Detalhe | `/campanha/{id}` | VPP por perfil + simulador de bônus |
| Histórico | `/historico` | 36 meses de dados + sazonalidade + insights |
| VPP | `/vpp` | Valor Por Ponto + waterfall de perfis |
| Previsão | `/previsao` | Probabilidade de próximas campanhas |
| Status | `/status` | Saúde dos 14 scrapers + progresso bootstrap |

---

## Comandos úteis

```bash
# Ver status de todos os containers
docker compose ps

# Logs em tempo real
docker compose logs -f app

# Reiniciar o sistema
docker compose restart app

# Forçar scrape imediato de uma fonte
curl -X POST "http://localhost:8000/api/scrape/trigger?source=smiles"

# Ver campanhas ativas agora
curl http://localhost:8000/api/promos/active | python3 -m json.tool

# Ver saúde do sistema
curl http://localhost:8000/api/health | python3 -m json.tool

# Atualizar o código (após receber nova versão)
docker compose down
tar -xzf nova-versao.tar.gz
docker compose up -d --build
```

---

## HTTPS (opcional, recomendado para uso contínuo)

Se você tem um domínio apontando para o servidor:

```bash
# Instala Nginx + Certbot e configura HTTPS automaticamente
sudo bash scripts/setup-production.sh SEU_DOMINIO.COM.BR
```

Sem domínio, o sistema funciona por IP na porta 8000.

---

## Configuração avançada (`.env`)

```bash
# Banco de dados
DATABASE_URL=postgresql://milesradar:SENHA@postgres:5432/milesradar

# WhatsApp (Evolution API)
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_API_KEY=SUA_CHAVE
EVOLUTION_INSTANCE_NAME=milesradar

# Filtros de alerta
ALERT_NUMBERS=5565999999999,5511888888888  # múltiplos números, separados por vírgula
MIN_BONUS_PCT=40                           # bônus mínimo para alertar (%)
MAX_CPM=20.0                               # CPM máximo (R$/1k) — não alerta se mais caro
PROGRAMS_WATCH=LATAM Pass,Smiles           # vazio = monitorar todos os programas
SILENT_START_HOUR=23                       # início do horário silencioso (BRT)
SILENT_END_HOUR=7                          # fim do horário silencioso (BRT)

# Bootstrap histórico
BOOTSTRAP_MONTHS=36                        # quantos meses coletar nos blogs
BOOTSTRAP_DELAY_SECONDS=3                  # delay entre páginas (evita bloqueio)

# Parser LLM (opcional — melhora extração de posts ambíguos)
ANTHROPIC_API_KEY=sk-ant-...              # API key da Anthropic
LLM_CONFIDENCE_THRESHOLD=0.7              # aciona LLM se confidence < este valor
LLM_ENABLED=true
```

---

## Como adicionar um novo scraper

1. Crie o arquivo `miles_radar/scrapers/nova_fonte.py`:

```python
from miles_radar.scrapers.base import BaseScraper, ScrapedItem
from typing import List

class NovaFonteScraper(BaseScraper):
    name = "novafonte"
    base_url = "https://novafonte.com.br"
    interval_minutes = 60

    async def scrape(self) -> List[ScrapedItem]:
        html = await self.fetch_with_retry(self.base_url + "/promocoes")
        return self._parse(html, self.base_url)

    async def scrape_bootstrap_page(self, page_url: str) -> List[ScrapedItem]:
        # Para blogs WordPress: page_url já vem como /page/N/
        html = await self.fetch_with_retry(page_url)
        return self._parse(html, page_url)

    def _parse(self, html: str, source_url: str) -> List[ScrapedItem]:
        # Extrai títulos e textos de promoções
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        items = []
        for article in soup.find_all("article")[:20]:
            # ... sua lógica de extração
            pass
        return items
```

2. Adicione ao scheduler em `miles_radar/scheduler/jobs.py` dentro de `phase2b`:
```python
("miles_radar.scrapers.nova_fonte", "NovaFonteScraper"),
```

3. Reinicie: `docker compose restart app`

---

## Arquitetura resumida

```
┌─────────────────────────────────────────────────────┐
│                   Miles Radar                       │
│                                                     │
│  14 scrapers ──→ Parser v1 (regex)                 │
│                      ↓ se confidence < 0.7         │
│                  Parser v2 (Claude API)             │
│                      ↓                             │
│               PostgreSQL (campanhas)               │
│                      ↓                             │
│  ┌─────────────────────────────────────────────┐  │
│  │ FastAPI                                      │  │
│  │  /api/health     /api/history               │  │
│  │  /api/promos     /api/vpp                   │  │
│  │  /api/analysis   /api/predictions           │  │
│  └─────────────────────────────────────────────┘  │
│                      ↓                             │
│  Dashboard (7 telas) + WhatsApp (Evolution API)   │
└─────────────────────────────────────────────────────┘
```

---

## Troubleshooting

**Dashboard não abre:**
```bash
docker compose ps  # verifique se miles_app está "running"
docker compose logs app --tail=30  # procure erros em vermelho
```

**WhatsApp não recebe alertas:**
```bash
# Verifique se a instância está conectada
curl http://localhost:8080/api/instances \
     -H "apikey: SUA_EVOLUTION_API_KEY"
# Se status != "open": gere novo QR code e escaneie novamente
```

**Bootstrap não progride:**
```bash
# Veja o progresso
curl http://localhost:8000/api/health | python3 -m json.tool | grep bootstrap
# Reinicia apenas o bootstrap (não interrompe o monitor)
docker compose restart app
```

**Banco de dados cheio:**
```bash
docker exec miles_postgres psql -U milesradar -c "SELECT count(*) FROM campaigns;"
# Limpa campanhas antigas (> 2 anos), mantém histórico recente
docker exec miles_postgres psql -U milesradar -c \
  "DELETE FROM campaigns WHERE published_at < NOW() - INTERVAL '2 years';"
```

---

## Suporte

- Issues: reporte via mensagem com o log completo do erro
- Logs: `docker compose logs app --tail=100 > log.txt`

---

*Miles Radar v2.0 · Fase 6 completa · Oracle Cloud Free Tier*
