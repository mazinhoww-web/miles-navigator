"""
Agendamento de todos os scrapers.
Correções:
- BUG 6: BootstrapState.last_updated atualizado a cada progresso
- BUG 7: page_url usa padrão WordPress /page/N/ correto para blogs
         e cada scraper define seu próprio padrão de paginação
"""
import asyncio, random, datetime as dt
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from miles_radar.logger import logger
from miles_radar.models.database import SessionLocal
from miles_radar.settings import settings


def _jitter(minutes: int) -> int:
    return int(minutes * random.uniform(0.8, 1.2))


async def _run_scraper(scraper_class):
    db = SessionLocal()
    try:
        await scraper_class().run(db_session=db)
    except Exception as e:
        logger.error(f"[Scheduler] {scraper_class.name}: {e}")
    finally:
        db.close()


def _bootstrap_page_url(scraper, page_num: int) -> str:
    """
    FIX BUG 7: cada tipo de site tem um padrão diferente de paginação.
    WordPress blogs usam /page/N/ — não ?page=N.
    Sites oficiais de programas geralmente não têm paginação histórica.
    """
    if page_num == 1:
        return scraper.base_url

    # Blogs WordPress (PP, MD, MDM, PPV) — padrão /page/N/
    wp_scrapers = {"passageirodeprimeira", "melhoresdestinos", "mestredasmilhas", "pontospravoar"}
    if scraper.name in wp_scrapers:
        # Cada blog tem sua categoria base diferente
        category_paths = {
            "passageirodeprimeira": "https://passageirodeprimeira.com/categorias/promocoes/page/{}/",
            "melhoresdestinos": "https://www.melhoresdestinos.com.br/milhas/page/{}/",
            "mestredasmilhas": "https://mestredasmilhas.com/category/promocoes/page/{}/",
            "pontospravoar": "https://pontospravoar.com/category/pontos-e-milhas/page/{}/",
        }
        return category_paths[scraper.name].format(page_num)

    # Para programas oficiais e bancos, não há arquivo histórico paginado
    # O bootstrap desses scrapers coleta apenas o que está disponível agora
    return None  # None = parar bootstrap para este tipo


async def _run_bootstrap(scraper_class, max_months: int):
    """
    Bootstrap histórico: crawl reverso paginado para popular o banco com dados passados.
    Funciona principalmente para blogs (PP, MD, MDM, PPV) que têm arquivo histórico.
    """
    from miles_radar.models.campaign import BootstrapState, Campaign
    from miles_radar.parsers.campaign_parser import CampaignParser

    scraper = scraper_class()
    db = SessionLocal()
    try:
        state = db.query(BootstrapState).filter(
            BootstrapState.source_name == scraper.name
        ).first()

        if state and state.is_complete:
            logger.info(f"[Bootstrap] {scraper.name} já completo ({state.total_campaigns_found} campanhas)")
            return

        if not state:
            state = BootstrapState(source_name=scraper.name, total_pages_scraped=0, total_campaigns_found=0)
            db.add(state)
            db.commit()

        target_date = dt.datetime.utcnow() - dt.timedelta(days=max_months * 30)
        logger.info(f"[Bootstrap] {scraper.name} — meta: {target_date.strftime('%Y-%m')}")

        parser = CampaignParser()
        # Retoma de onde parou
        start_page = (state.total_pages_scraped or 0) + 1

        for page_num in range(start_page, 400):
            page_url = _bootstrap_page_url(scraper, page_num)

            # Scrapers sem paginação histórica: faz 1 scrape do estado atual e encerra
            if page_url is None:
                if page_num == 1:
                    items = await scraper.scrape()
                    _save_items(items, parser, db, state)
                state.is_complete = True
                db.commit()
                break

            if not hasattr(scraper, 'scrape_bootstrap_page'):
                logger.warning(f"[Bootstrap] {scraper.name} sem scrape_bootstrap_page — encerrando")
                state.is_complete = True
                db.commit()
                break

            items = await scraper.scrape_bootstrap_page(page_url)

            if not items:
                logger.info(f"[Bootstrap] {scraper.name} pág {page_num} vazia — encerrando")
                state.is_complete = True
                db.commit()
                break

            new_count = _save_items(items, parser, db, state)

            # Verifica se atingiu a data-alvo
            oldest = min((i.published_at for i in items if i.published_at), default=None)
            if oldest and oldest < target_date:
                logger.info(f"[Bootstrap] {scraper.name} atingiu data-alvo ({oldest.strftime('%Y-%m')})")
                state.is_complete = True

            # FIX BUG 6: atualiza last_updated e oldest a cada página
            state.total_pages_scraped = page_num
            state.total_campaigns_found += len(items)
            if oldest:
                state.oldest_month_collected = oldest.strftime("%Y-%m")
            state.last_updated = dt.datetime.utcnow()
            db.commit()

            logger.info(
                f"[Bootstrap] {scraper.name} pág {page_num}: "
                f"{new_count} novas | mais antigo: {oldest.strftime('%Y-%m') if oldest else '?'}"
            )

            if state.is_complete:
                break

            await asyncio.sleep(settings.bootstrap_delay_seconds * random.uniform(0.8, 1.3))

    except Exception as e:
        logger.error(f"[Bootstrap] {scraper.name}: {e}")
    finally:
        db.close()


def _save_items(items, parser, db, state):
    """Salva itens novos no banco. Retorna contagem de novos."""
    from miles_radar.models.campaign import Campaign
    new_count = 0
    for item in items:
        campaign = parser.parse(item)
        if campaign:
            existing = db.query(Campaign).filter(
                Campaign.content_hash == campaign.content_hash
            ).first()
            if not existing:
                db.add(campaign)
                new_count += 1
    db.commit()
    return new_count


def _load_scrapers():
    scrapers = []
    from miles_radar.scrapers.passageiro_de_primeira import PassageiroDePrimeiraScraper
    from miles_radar.scrapers.smiles import SmilesScraper
    from miles_radar.scrapers.latam_pass import LatamPassScraper
    scrapers.extend([PassageiroDePrimeiraScraper, SmilesScraper, LatamPassScraper])

    phase2b = [
        ("miles_radar.scrapers.azul", "AzulScraper"),
        ("miles_radar.scrapers.livelo", "LiveloScraper"),
        ("miles_radar.scrapers.esfera", "EsferaScraper"),
        ("miles_radar.scrapers.melhores_destinos", "MelhoresDestinosScraper"),
        ("miles_radar.scrapers.mestre_das_milhas", "MestreDasMilhasScraper"),
        ("miles_radar.scrapers.pontos_pra_voar", "PontosPraVoarScraper"),
        ("miles_radar.scrapers.itau_iupp", "ItauIuppScraper"),
        ("miles_radar.scrapers.nubank", "NubankScraper"),
        ("miles_radar.scrapers.c6", "C6Scraper"),
        ("miles_radar.scrapers.inter", "InterScraper"),
        ("miles_radar.scrapers.sicoob", "SicoobScraper"),
    ]
    for module_path, class_name in phase2b:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            scrapers.append(getattr(mod, class_name))
        except Exception as e:
            logger.warning(f"[Scheduler] Não foi possível carregar {class_name}: {e}")
    return scrapers


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    scrapers = _load_scrapers()
    for sc in scrapers:
        interval = _jitter(sc.interval_minutes)
        scheduler.add_job(_run_scraper, IntervalTrigger(minutes=interval),
            args=[sc], id=f"monitor_{sc.name}", name=f"Monitor:{sc.name}",
            replace_existing=True, max_instances=1)
    for sc in scrapers:
        scheduler.add_job(_run_bootstrap, IntervalTrigger(hours=24),
            args=[sc, settings.bootstrap_months],
            id=f"bootstrap_{sc.name}", name=f"Bootstrap:{sc.name}",
            replace_existing=True, max_instances=1, next_run_time=None)
    logger.info(f"[Scheduler] {len(scrapers)} scrapers registrados")

    # Health check a cada 30 minutos
    from miles_radar.scheduler.health_check import check_scraper_health
    scheduler.add_job(
        check_scraper_health,
        trigger=IntervalTrigger(minutes=30),
        id="health_check",
        name="Health Check",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("[Scheduler] Health check agendado a cada 30 min")

    # Apify sync — ativo automaticamente quando APIFY_TOKEN está configurado
    if settings.apify_token:
        scheduler.add_job(
            apify_sync_job,
            trigger=IntervalTrigger(minutes=30),
            id="apify_sync",
            name="Apify Sync — todas as fontes",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("[Scheduler] Apify sync agendado a cada 30 min")

    return scheduler


# ─── Apify Sync Job (substitui scrapers Playwright por Actors na nuvem) ──────

async def apify_sync_job():
    """
    Job centralizado que sincroniza todas as 14 fontes via Apify REST API.
    Roda a cada 30 minutos. Ativa-se automaticamente quando APIFY_TOKEN está configurado.
    """
    from datetime import timedelta
    from miles_radar.scrapers.apify_client import ApifyClient
    from miles_radar.parsers.campaign_parser import CampaignParser
    from miles_radar.models.database import SessionLocal
    from miles_radar.models.campaign import Campaign, ScrapeRun
    from miles_radar.notifier.whatsapp import send_campaign_alert

    if not settings.apify_token:
        logger.debug("[apify_sync] APIFY_TOKEN não configurado — job ignorado")
        return

    client = ApifyClient()
    parser = CampaignParser()
    since = datetime.utcnow() - timedelta(hours=1)

    ACTOR_MAP = {
        "passageirodeprimeira": settings.apify_actor_passageirodeprimeira,
        "melhoresdestinos":     settings.apify_actor_melhoresdestinos,
        "mestredasmilhas":      settings.apify_actor_mestredasmilhas,
        "pontospravoar":        settings.apify_actor_pontospravoar,
        "smiles":               settings.apify_actor_smiles,
        "latampass":            settings.apify_actor_latampass,
        "azul":                 settings.apify_actor_azul,
        "livelo":               settings.apify_actor_livelo,
        "esfera":               settings.apify_actor_esfera,
        "itau_iupp":            settings.apify_actor_itau_iupp,
        "nubank":               settings.apify_actor_nubank,
        "c6":                   settings.apify_actor_c6,
        "inter":                settings.apify_actor_inter,
        "sicoob":               settings.apify_actor_sicoob,
    }

    db = SessionLocal()
    total_new = 0
    try:
        for source_name, actor_id in ACTOR_MAP.items():
            if not actor_id:
                continue
            run = ScrapeRun(source_name=source_name, is_bootstrap=False,
                            started_at=datetime.utcnow(), status="running")
            db.add(run)
            db.commit()
            t0 = datetime.utcnow()
            found = 0
            new_count = 0
            try:
                items = await client.sync_source(source_name, actor_id, since)
                found = len(items)
                for item in items:
                    campaign = parser.parse(item)
                    if not campaign:
                        continue
                    existing = db.query(Campaign).filter(
                        Campaign.content_hash == campaign.content_hash
                    ).first()
                    if not existing:
                        db.add(campaign)
                        db.commit()
                        db.refresh(campaign)
                        new_count += 1
                        total_new += 1
                        try:
                            await send_campaign_alert(campaign)
                        except Exception as e:
                            logger.warning(f"[apify_sync] Alerta falhou: {e}")
                run.status = "ok"
            except Exception as e:
                logger.error(f"[apify_sync] Erro em {source_name}: {e}")
                run.status = "error"
            finally:
                run.campaigns_found = found
                run.campaigns_new = new_count
                run.finished_at = datetime.utcnow()
                run.duration_seconds = (run.finished_at - t0).total_seconds()
                db.commit()

        logger.info(f"[apify_sync] Completo. {total_new} campanhas novas.")
    finally:
        db.close()
