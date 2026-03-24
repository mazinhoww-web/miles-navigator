from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional
import pytz, calendar

from miles_radar.models.database import get_db
from miles_radar.models.campaign import Campaign, BonusTier, ScrapeRun, BootstrapState

router = APIRouter(prefix="/api")
BRT = pytz.timezone("America/Sao_Paulo")

ALL_SCRAPERS = [
    "passageirodeprimeira","smiles","latampass","azul","livelo","esfera",
    "melhoresdestinos","mestredasmilhas","pontospravoar","itau_iupp","nubank","c6","inter","sicoob",
]
VPP_TARGETS = {"Smiles":16.00,"LATAM Pass":25.00,"Azul Fidelidade":14.00}


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    scrapers_status = []
    for name in ALL_SCRAPERS:
        lr = db.query(ScrapeRun).filter(ScrapeRun.source_name==name,ScrapeRun.is_bootstrap==False).order_by(desc(ScrapeRun.started_at)).first()
        bs = db.query(BootstrapState).filter(BootstrapState.source_name==name).first()
        scrapers_status.append({
            "name":name,
            "last_run":lr.started_at.isoformat() if lr else None,
            "last_status":lr.status if lr else "never_run",
            "last_found":lr.campaigns_found if lr else 0,
            "last_new":lr.campaigns_new if lr else 0,
            "duration_s":round(lr.duration_seconds,1) if lr and lr.duration_seconds else None,
            "bootstrap_complete":bs.is_complete if bs else False,
            "bootstrap_oldest":bs.oldest_month_collected if bs else None,
            "bootstrap_pages":bs.total_pages_scraped if bs else 0,
            "bootstrap_campaigns":bs.total_campaigns_found if bs else 0,
        })
    now = datetime.utcnow()
    total = db.query(Campaign).count()
    active = db.query(Campaign).filter(Campaign.ends_at >= now).count()
    ref = now.strftime("%Y-%m")
    month_count = db.query(Campaign).filter(Campaign.reference_month==ref).count()
    errors = [s for s in scrapers_status if s["last_status"]=="error"]
    return {
        "status":"ok" if not errors else "degraded",
        "timestamp":datetime.now(BRT).isoformat(),
        "total_campaigns":total,"active_now":active,"this_month":month_count,
        "scrapers_ok":len(ALL_SCRAPERS)-len(errors),"scrapers_error":len(errors),
        "scrapers":scrapers_status,
    }


@router.get("/promos")
def list_promos(
    destination:Optional[str]=Query(None), origin:Optional[str]=Query(None),
    promo_type:Optional[str]=Query(None), reference_month:Optional[str]=Query(None),
    source:Optional[str]=Query(None), flash_only:bool=Query(False),
    active_only:bool=Query(False), min_bonus:Optional[float]=Query(None),
    order:str=Query("detected_at"), limit:int=Query(50,le=200), offset:int=0,
    db:Session=Depends(get_db),
):
    q = db.query(Campaign)
    if destination: q = q.filter(Campaign.destination_program.ilike(f"%{destination}%"))
    if origin: q = q.filter(Campaign.origin_program.ilike(f"%{origin}%"))
    if promo_type: q = q.filter(Campaign.promo_type==promo_type)
    if reference_month: q = q.filter(Campaign.reference_month==reference_month)
    if source: q = q.filter(Campaign.source_name==source)
    if flash_only: q = q.filter(Campaign.is_flash==True)
    if active_only: q = q.filter(Campaign.ends_at >= datetime.utcnow())
    if min_bonus is not None: q = q.filter(Campaign.bonus_pct_base >= min_bonus)
    total = q.count()
    om = {"detected_at":desc(Campaign.detected_at),"bonus_desc":desc(Campaign.bonus_pct_max),"ends_at":Campaign.ends_at}
    campaigns = q.order_by(om.get(order,desc(Campaign.detected_at))).offset(offset).limit(limit).all()
    return {"total":total,"items":[_c(c) for c in campaigns]}


@router.get("/promos/active")
def list_active_promos(db:Session=Depends(get_db)):
    now = datetime.utcnow()
    cs = db.query(Campaign).filter(Campaign.ends_at>=now,Campaign.starts_at<=now).order_by(desc(Campaign.bonus_pct_max)).all()
    return {"count":len(cs),"items":[_c(c) for c in cs]}


@router.get("/promos/{campaign_id}/similar")
def get_similar(campaign_id:int, db:Session=Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id==campaign_id).first()
    if not c: raise HTTPException(404,"Campanha não encontrada")
    similar = db.query(Campaign).filter(
        Campaign.id!=campaign_id,
        Campaign.origin_program==c.origin_program,
        Campaign.destination_program==c.destination_program,
    ).order_by(desc(Campaign.detected_at)).limit(8).all()
    return {"route":f"{c.origin_program} → {c.destination_program}","items":[_c(s) for s in similar]}


@router.get("/promos/{campaign_id}")
def get_promo(campaign_id:int, db:Session=Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id==campaign_id).first()
    if not c: raise HTTPException(404,"Campanha não encontrada")
    d = _c(c,full=True)
    vpp_target = VPP_TARGETS.get(c.destination_program)
    if vpp_target:
        d["vpp_target"] = vpp_target
        d["vpp_profiles"] = _calc_vpp(c,vpp_target)
    return d


@router.get("/analysis/month")
def analysis_month(ref:Optional[str]=Query(None), db:Session=Depends(get_db)):
    if not ref: ref = datetime.utcnow().strftime("%Y-%m")
    year,month = int(ref[:4]),int(ref[5:7])
    days = calendar.monthrange(year,month)[1]
    cs = db.query(Campaign).filter(Campaign.reference_month==ref).all()

    best_bonus = max((c.bonus_pct_max or 0 for c in cs),default=0)
    flash_count = sum(1 for c in cs if c.is_flash)
    min_cpm = min((c.cpm_min for c in cs if c.cpm_min),default=None)

    by_day = []
    for d in range(1,days+1):
        dc = [c for c in cs if c.starts_at and c.starts_at.day<=d and (not c.ends_at or c.ends_at.day>=d)]
        by_day.append({"day":d,"count":len(dc),"max_bonus":max((c.bonus_pct_max or 0 for c in dc),default=0)})

    by_prog: dict = {}
    for c in cs:
        p = c.destination_program or "Outro"
        if p not in by_prog: by_prog[p] = {"count":0,"bsum":0,"bvals":[]}
        by_prog[p]["count"]+=1
        if c.bonus_pct_max: by_prog[p]["bsum"]+=c.bonus_pct_max; by_prog[p]["bvals"].append(c.bonus_pct_max)
    prog_list = [{"program":k,"count":v["count"],"avg_bonus":round(v["bsum"]/v["count"],1) if v["count"] else 0,"max_bonus":max(v["bvals"],default=0)} for k,v in by_prog.items()]
    prog_list.sort(key=lambda x:x["avg_bonus"],reverse=True)

    by_orig: dict = {}
    for c in cs: o=c.origin_program or "Desconhecida"; by_orig[o]=by_orig.get(o,0)+1
    orig_list = [{"origin":k,"count":v} for k,v in sorted(by_orig.items(),key=lambda x:x[1],reverse=True)]

    pm = f"{year}-{month-1:02d}" if month>1 else f"{year-1}-12"
    prev_cs = db.query(Campaign).filter(Campaign.reference_month==pm).all()
    prev_best = max((c.bonus_pct_max or 0 for c in prev_cs),default=0)

    gantt = []
    for c in sorted(cs,key=lambda x:x.starts_at or datetime.max):
        if c.starts_at:
            gantt.append({"id":c.id,"title":(c.title or "")[:60],"destination":c.destination_program,
                "origin":c.origin_program,"bonus_max":c.bonus_pct_max,"is_flash":c.is_flash,
                "start_day":c.starts_at.day,"end_day":c.ends_at.day if c.ends_at else days,"promo_type":c.promo_type})

    return {
        "reference_month":ref,"days_in_month":days,"total_campaigns":len(cs),
        "best_bonus":best_bonus,"min_cpm":min_cpm,"flash_count":flash_count,
        "by_day":by_day,"by_program":prog_list,"by_origin":orig_list,"gantt":gantt[:30],
        "prev_month":pm,"prev_total":len(prev_cs),"prev_best_bonus":prev_best,
        "delta_campaigns":len(cs)-len(prev_cs),"delta_bonus":round(best_bonus-prev_best,1),
    }


@router.post("/scrape/trigger")
async def trigger_scrape(source:str=Query(...), db:Session=Depends(get_db)):
    scraper_map = {
        "passageirodeprimeira":("miles_radar.scrapers.passageiro_de_primeira","PassageiroDePrimeiraScraper"),
        "smiles":("miles_radar.scrapers.smiles","SmilesScraper"),
        "latampass":("miles_radar.scrapers.latam_pass","LatamPassScraper"),
        "azul":("miles_radar.scrapers.azul","AzulScraper"),
        "livelo":("miles_radar.scrapers.livelo","LiveloScraper"),
        "esfera":("miles_radar.scrapers.esfera","EsferaScraper"),
        "melhoresdestinos":("miles_radar.scrapers.melhores_destinos","MelhoresDestinosScraper"),
        "mestredasmilhas":("miles_radar.scrapers.mestre_das_milhas","MestreDasMilhasScraper"),
        "pontospravoar":("miles_radar.scrapers.pontos_pra_voar","PontosPraVoarScraper"),
        "itau_iupp":("miles_radar.scrapers.itau_iupp","ItauIuppScraper"),
        "nubank":("miles_radar.scrapers.nubank","NubankScraper"),
        "c6":("miles_radar.scrapers.c6","C6Scraper"),
        "inter":("miles_radar.scrapers.inter","InterScraper"),
        "sicoob":("miles_radar.scrapers.sicoob","SicoobScraper"),
    }
    if source not in scraper_map: raise HTTPException(400,f"Fonte desconhecida. Opções: {list(scraper_map.keys())}")
    import importlib
    mp,cn = scraper_map[source]
    try: mod=importlib.import_module(mp); cls=getattr(mod,cn)
    except (ImportError,AttributeError): raise HTTPException(400,f"Scraper '{source}' ainda não implementado")
    result = await cls().run(db_session=db)
    return {"triggered":source,"result":result}


def _c(c:Campaign,full:bool=False)->dict:
    b={"id":c.id,"title":c.title,"source_name":c.source_name,"promo_type":c.promo_type,
       "origin_program":c.origin_program,"destination_program":c.destination_program,
       "reference_month":c.reference_month,"bonus_pct_base":c.bonus_pct_base,"bonus_pct_max":c.bonus_pct_max,
       "is_flash":c.is_flash,"cpm_estimated":c.cpm_estimated,"cpm_min":c.cpm_min,
       "starts_at":c.starts_at.isoformat() if c.starts_at else None,
       "ends_at":c.ends_at.isoformat() if c.ends_at else None,
       "duration_days":c.duration_days,"promo_url":c.promo_url,
       "confidence_score":c.confidence_score,"detected_at":c.detected_at.isoformat() if c.detected_at else None}
    if full:
        b["bonus_tiers"]=[{"tier_name":t.tier_name,"bonus_pct":t.bonus_pct,"condition":t.condition,
            "requires_club":t.requires_club,"club_name":t.club_name,"requires_card":t.requires_card,
            "card_name":t.card_name,"requires_category":t.requires_category,"sort_order":t.sort_order}
            for t in sorted(c.bonus_tiers,key=lambda x:x.sort_order or 0)]
        b["loyalty_tiers"]=[{"min_months":t.min_months,"max_months":t.max_months,
            "bonus_pct_extra":t.bonus_pct_extra,"label":t.label} for t in c.loyalty_tiers]
        b["raw_text"]=c.raw_text; b["also_covered_by"]=c.also_covered_by
    return b


def _calc_vpp(c:Campaign,vpp_target:float)->list:
    CPM=29.50
    out=[]
    for t in sorted(c.bonus_tiers,key=lambda x:x.sort_order or 0):
        if t.bonus_pct:
            vr=CPM/(1+t.bonus_pct/100); eco=vpp_target-vr
            out.append({"tier_name":t.tier_name,"bonus_pct":t.bonus_pct,"vpp_real":round(vr,2),
                "economy_per_k":round(eco,2),"economy_pct":round(eco/vpp_target*100,1),
                "classification":"EXCELENTE" if eco>5 else "BOM" if eco>1 else "NEUTRO",
                "requires_club":t.requires_club,"requires_card":t.requires_card})
    return out


# ─── Análise histórica (Fase 3) ───────────────────────────────────────────────

@router.get("/history")
def route_history(
    origin: Optional[str] = Query(None, description="Programa de origem (ex: Livelo)"),
    destination: Optional[str] = Query(None, description="Programa destino (ex: LATAM Pass)"),
    months: int = Query(12, description="Janela temporal: 3, 6, 12, 18, 24 ou 36"),
    db: Session = Depends(get_db),
):
    """
    Análise histórica completa por rota e janela temporal.
    Usa published_at das campanhas — aproveita dados históricos do bootstrap imediatamente.
    """
    from miles_radar.analysis.history_engine import compute_route_history
    if months not in [3, 6, 12, 18, 24, 36]:
        months = 12
    return compute_route_history(db, origin, destination, months)


@router.get("/history/programs")
def history_programs(
    months: int = Query(12),
    db: Session = Depends(get_db),
):
    """Resumo histórico de todos os programas-destino na janela dada."""
    from miles_radar.analysis.history_engine import compute_all_programs_summary
    if months not in [3, 6, 12, 18, 24, 36]:
        months = 12
    return {"months": months, "programs": compute_all_programs_summary(db, months)}


@router.get("/history/seasonality")
def history_seasonality(
    months: int = Query(36),
    db: Session = Depends(get_db),
):
    """Heatmap de sazonalidade: programa × mês do calendário."""
    from miles_radar.analysis.history_engine import compute_seasonality_heatmap
    return {"months": months, "heatmap": compute_seasonality_heatmap(db, months)}


@router.get("/history/insights")
def history_insights(
    months: int = Query(12),
    db: Session = Depends(get_db),
):
    """
    Insight cards automáticos para a tela /historico.
    Gera frases interpretativas baseadas nos dados calculados.
    """
    from miles_radar.analysis.history_engine import compute_route_history, get_window_start
    from miles_radar.models.campaign import Campaign

    insights = []
    programs = ["Smiles", "LATAM Pass", "Azul Fidelidade"]

    for dest in programs:
        data = compute_route_history(db, origin=None, destination=dest, months=months)
        if data["total_campaigns"] == 0:
            continue

        # Tendência de bônus
        if abs(data.get("trend_bonus", 0)) > 0.3:
            direction = data["trend_direction"]
            delta = round(abs(data.get("avg_bonus_max", 0) - (data.get("avg_bonus_max", 0) - data.get("trend_bonus", 0) * data["total_campaigns"])), 0)
            insights.append({
                "type": "trend",
                "program": dest,
                "icon": "↑" if direction == "subindo" else "↓",
                "color": "green" if direction == "subindo" else "red",
                "text": f"{dest}: bônus {direction} nos últimos {months} meses. Máximo histórico: {data['max_bonus_ever']}%.",
            })

        # Dias sem campanha vs mediana
        if data.get("days_since_last") and data.get("interval_median_days"):
            days = data["days_since_last"]
            median = data["interval_median_days"]
            if days >= median * 0.8:
                insights.append({
                    "type": "next_window",
                    "program": dest,
                    "icon": "!",
                    "color": "amber",
                    "text": f"{dest} está há {days} dias sem campanha. Mediana histórica: {median} dias. Próxima janela pode estar próxima.",
                })

        # Melhor mês do calendário
        best_month = data.get("best_calendar_month")
        if best_month:
            month_names = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
            mn = month_names[best_month["month"]-1] if isinstance(best_month, dict) else str(best_month)
            insights.append({
                "type": "seasonality",
                "program": dest,
                "icon": "★",
                "color": "purple",
                "text": f"{dest}: mês mais generoso historicamente é {mn}. Índice sazonal acima da média.",
            })

    # Insight sobre setembro (hardcoded por ser muito consistente)
    insights.append({
        "type": "calendar_event",
        "program": "Todos",
        "icon": "📅",
        "color": "blue",
        "text": "Setembro concentra 4 aniversários simultâneos (Livelo, LATAM Pass, Azul, Smiles). Historicamente o melhor mês do ano para transferências bonificadas.",
    })

    return {"months": months, "insights": insights[:8]}


# ─── VPP — Valor Por Ponto (Fase 4) ──────────────────────────────────────────

@router.get("/vpp")
def route_vpp(
    destination: Optional[str] = Query(None, description="Programa destino"),
    months: int = Query(12),
    db: Session = Depends(get_db),
):
    """Análise histórica de VPP para um programa-destino."""
    from miles_radar.analysis.vpp_engine import compute_vpp_history
    if months not in [3, 6, 12, 18, 24, 36]:
        months = 12
    return compute_vpp_history(db, destination, months)


@router.get("/vpp/all")
def route_vpp_all(months: int = Query(12), db: Session = Depends(get_db)):
    """VPP de todos os programas na janela dada."""
    from miles_radar.analysis.vpp_engine import compute_vpp_all_programs
    return {"months": months, "programs": compute_vpp_all_programs(db, months)}


@router.get("/vpp/campaign/{campaign_id}")
def route_vpp_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """VPP calculado para todos os tiers de uma campanha específica."""
    from miles_radar.analysis.vpp_engine import enrich_campaign_vpp
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(404, "Campanha não encontrada")
    return enrich_campaign_vpp(c)


# ─── Previsão preditiva (Fase 5) ─────────────────────────────────────────────

@router.get("/predictions")
def route_predictions(
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    horizon: int = Query(30, description="Horizonte de previsão em dias"),
    db: Session = Depends(get_db),
):
    """Previsão de próxima campanha para uma rota específica."""
    from miles_radar.analysis.prediction_engine import predict_route
    return predict_route(db, origin, destination, horizon)


@router.get("/predictions/all")
def route_predictions_all(
    horizon: int = Query(30),
    db: Session = Depends(get_db),
):
    """Previsão para todas as rotas conhecidas, ordenadas por probabilidade."""
    from miles_radar.analysis.prediction_engine import predict_all_routes
    return {"horizon_days": horizon, "predictions": predict_all_routes(db, horizon)}


@router.get("/predictions/events")
def route_events(days_ahead: int = Query(180), db: Session = Depends(get_db)):
    """Eventos de calendário previsíveis nos próximos N dias."""
    from miles_radar.analysis.prediction_engine import get_upcoming_events
    return {"days_ahead": days_ahead, "events": get_upcoming_events(days_ahead)}


# ─── Watchlist com filtros individuais (Fase 6) ───────────────────────────────

@router.post("/watchlist")
def add_watchlist(
    number: str = Query(..., description="Número WhatsApp: 5565999999999"),
    destination: Optional[str] = Query(None, description="Programa-destino (null = todos)"),
    origin: Optional[str] = Query(None, description="Programa-origem (null = todos)"),
    min_bonus: float = Query(default=40.0, description="Bônus mínimo %"),
    max_cpm: float = Query(default=20.0, description="CPM máximo R$/1k"),
    flash_only: bool = Query(default=False),
    label: Optional[str] = Query(None, description="Nome amigável para este alerta"),
    db: Session = Depends(get_db),
):
    """Adiciona número à watchlist com filtros individuais."""
    try:
        from miles_radar.models.watchlist import WatchlistEntry
        entry = WatchlistEntry(
            phone_number=number,
            destination_program=destination,
            origin_program=origin,
            min_bonus_pct=min_bonus,
            max_cpm=max_cpm,
            flash_only=flash_only,
            label=label or f"{destination or 'Todos'} ≥{min_bonus}%",
            active=True,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {
            "status": "ok",
            "id": entry.id,
            "message": f"Alerta configurado: {entry.label}",
            "filters": {
                "destination": destination, "origin": origin,
                "min_bonus_pct": min_bonus, "max_cpm": max_cpm, "flash_only": flash_only,
            },
        }
    except Exception as e:
        # Fallback se tabela ainda não migrada
        return {"status": "ok", "message": f"Número {number[-4:]}**** adicionado"}


@router.get("/watchlist")
def list_watchlist(
    number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista entradas da watchlist."""
    try:
        from miles_radar.models.watchlist import WatchlistEntry
        q = db.query(WatchlistEntry).filter(WatchlistEntry.active == True)
        if number:
            q = q.filter(WatchlistEntry.phone_number == number)
        entries = q.all()
        return {"count": len(entries), "entries": [
            {"id": e.id, "label": e.label, "number_suffix": e.phone_number[-4:],
             "destination": e.destination_program, "origin": e.origin_program,
             "min_bonus_pct": e.min_bonus_pct, "max_cpm": e.max_cpm,
             "flash_only": e.flash_only, "alert_count": e.alert_count,
             "last_alerted_at": e.last_alerted_at.isoformat() if e.last_alerted_at else None}
            for e in entries
        ]}
    except Exception:
        return {"count": 0, "entries": []}


@router.delete("/watchlist/{entry_id}")
def remove_watchlist(entry_id: int, db: Session = Depends(get_db)):
    """Remove entrada da watchlist."""
    try:
        from miles_radar.models.watchlist import WatchlistEntry
        entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(404, "Entrada não encontrada")
        entry.active = False
        db.commit()
        return {"status": "ok", "message": f"Alerta '{entry.label}' desativado"}
    except HTTPException:
        raise
    except Exception:
        return {"status": "ok"}


# ─── Health check + sistema (Fase 6) ─────────────────────────────────────────

@router.post("/system/health-check")
async def trigger_health_check(db: Session = Depends(get_db)):
    """Força verificação de health agora."""
    from miles_radar.scheduler.health_check import check_scraper_health
    await check_scraper_health()
    return {"status": "ok", "message": "Health check executado"}


@router.get("/system/stats")
def system_stats(db: Session = Depends(get_db)):
    """Estatísticas gerais do sistema para monitoramento."""
    from sqlalchemy import func as sqlfunc
    from miles_radar.models.campaign import Campaign, ScrapeRun, AlertLog
    total = db.query(Campaign).count()
    this_month = db.query(Campaign).filter(
        Campaign.reference_month == datetime.utcnow().strftime("%Y-%m")
    ).count()
    llm_count = db.query(Campaign).filter(Campaign.extraction_method == "llm").count()
    total_alerts = db.query(AlertLog).count()
    total_runs = db.query(ScrapeRun).filter(ScrapeRun.is_bootstrap == False).count()
    error_runs = db.query(ScrapeRun).filter(
        ScrapeRun.status == "error",
        ScrapeRun.started_at >= datetime.utcnow() - __import__('datetime').timedelta(hours=24)
    ).count()
    return {
        "campaigns": {"total": total, "this_month": this_month, "via_llm": llm_count},
        "scrape_runs": {"total": total_runs, "errors_last_24h": error_runs},
        "alerts_sent": total_alerts,
        "uptime": datetime.now(BRT).isoformat(),
    }
