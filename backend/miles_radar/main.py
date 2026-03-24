import asyncio, os, datetime as dt
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from miles_radar.logger import logger
from miles_radar.models.database import engine, Base
from miles_radar.api.routes import router
from miles_radar.scheduler.jobs import create_scheduler, _run_bootstrap, _load_scrapers
from miles_radar.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Miles Radar v2 iniciando...")
    # Importa todos os modelos para garantir que as tabelas são criadas
    from miles_radar.models.campaign import (
        Campaign, BonusTier, LoyaltyDurationTier, ScrapeRun, AlertLog,
        BootstrapState, VppReference
    )
    try:
        from miles_radar.models.watchlist import WatchlistEntry
    except ImportError:
        pass
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados pronto")
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    # Dispara scrape inicial imediato para todos os scrapers
    scrapers = _load_scrapers()
    for sc in scrapers:
        try:
            scheduler.modify_job(f"monitor_{sc.name}", next_run_time=dt.datetime.now())
        except Exception:
            pass

    # Bootstrap em background — prioridade para os blogs de alta cobertura
    async def run_all_bootstraps():
        await asyncio.sleep(20)  # aguarda sistema estabilizar
        priority_scrapers = [
            s for s in scrapers
            if s.name in ("passageirodeprimeira", "melhoresdestinos", "mestredasmilhas", "pontospravoar")
        ]
        # Prioridade alta em paralelo
        await asyncio.gather(
            *[_run_bootstrap(s, settings.bootstrap_months) for s in priority_scrapers],
            return_exceptions=True
        )
        # Demais fontes em sequência (menos crítico, evita sobrecarga)
        rest = [s for s in scrapers if s not in priority_scrapers]
        for s in rest:
            await _run_bootstrap(s, min(settings.bootstrap_months, 24))
            await asyncio.sleep(5)

    asyncio.create_task(run_all_bootstraps())
    logger.info(f"Miles Radar online — {len(scrapers)} scrapers ativos — http://0.0.0.0:8000")
    yield
    scheduler.shutdown()
    logger.info("Miles Radar encerrado")

app = FastAPI(title="Miles Radar", version="2.0.0", lifespan=lifespan)
app.include_router(router)

if os.path.exists("miles_radar/dashboard/static"):
    app.mount("/static", StaticFiles(directory="miles_radar/dashboard/static"), name="static")

templates = Jinja2Templates(directory="miles_radar/dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/analise-mensal", response_class=HTMLResponse)
async def analise_mensal(request: Request):
    return templates.TemplateResponse("analise_mensal.html", {"request": request})

@app.get("/campanha/{campaign_id}", response_class=HTMLResponse)
async def campanha_detail(request: Request, campaign_id: int):
    return templates.TemplateResponse("campanha.html", {"request": request, "campaign_id": campaign_id})

@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

@app.get("/historico", response_class=HTMLResponse)
async def historico(request: Request):
    return templates.TemplateResponse("historico.html", {"request": request})

@app.get("/vpp", response_class=HTMLResponse)
async def vpp_page(request: Request):
    return templates.TemplateResponse("vpp.html", {"request": request})

@app.get("/previsao", response_class=HTMLResponse)
async def previsao(request: Request):
    return templates.TemplateResponse("previsao.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok", "service": "miles-radar", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("miles_radar.main:app", host="0.0.0.0", port=8000, reload=False)
