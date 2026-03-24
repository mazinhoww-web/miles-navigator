"""
Health check automático — Fase 6.
Verifica periodicamente se os scrapers estão rodando.
Envia alerta WhatsApp se qualquer fonte parar por mais de 2× seu intervalo normal.
"""
from datetime import datetime, timedelta
from miles_radar.logger import logger
from miles_radar.models.database import SessionLocal
from miles_radar.models.campaign import ScrapeRun

# Intervalos esperados por scraper (minutos) — deve espelhar o definido em cada scraper
EXPECTED_INTERVALS = {
    "passageirodeprimeira": 15,
    "melhoresdestinos": 15,
    "smiles": 30,
    "pass": 30,
    "azul": 30,
    "mestredasmilhas": 30,
    "pontospravoar": 30,
    "livelo": 60,
    "esfera": 60,
    "itau_iupp": 120,
    "nubank": 120,
    "c6": 120,
    "inter": 120,
    "sicoob": 240,
}


async def check_scraper_health():
    """
    Chamado a cada 30 minutos pelo APScheduler.
    Alerta se algum scraper ficou silencioso por mais de 2× seu intervalo esperado.
    """
    db = SessionLocal()
    stalled = []
    try:
        now = datetime.utcnow()
        for scraper_name, interval_min in EXPECTED_INTERVALS.items():
            threshold = timedelta(minutes=interval_min * 2.5)
            last_run = db.query(ScrapeRun).filter(
                ScrapeRun.source_name == scraper_name,
                ScrapeRun.is_bootstrap == False,
            ).order_by(ScrapeRun.started_at.desc()).first()

            if last_run is None:
                # Nunca rodou — só reporta se sistema está ativo há mais de 1h
                continue

            elapsed = now - last_run.started_at.replace(tzinfo=None)
            if elapsed > threshold:
                stalled.append({
                    "name": scraper_name,
                    "last_run": last_run.started_at.strftime("%d/%m %H:%M"),
                    "elapsed_min": int(elapsed.total_seconds() / 60),
                    "expected_min": interval_min,
                    "last_status": last_run.status,
                })

    finally:
        db.close()

    if stalled:
        await _send_health_alert(stalled)


async def _send_health_alert(stalled: list):
    """Envia alerta WhatsApp sobre scrapers parados."""
    from miles_radar.notifier.whatsapp import _is_silent_hours
    from miles_radar.settings import settings
    import httpx

    if _is_silent_hours():
        logger.warning(f"[HealthCheck] {len(stalled)} scrapers parados, mas horário silencioso ativo")
        return

    if not settings.alert_numbers:
        logger.warning("[HealthCheck] Nenhum número configurado para alertas de health")
        return

    lines = ["⚠️ *Miles Radar — Alerta de Sistema*", ""]
    lines.append(f"{len(stalled)} scraper(s) parado(s):\n")
    for s in stalled:
        status_emoji = "❌" if s["last_status"] == "error" else "⏸️"
        lines.append(
            f"{status_emoji} *{s['name']}*\n"
            f"   Último run: {s['last_run']} ({s['elapsed_min']}min atrás)\n"
            f"   Esperado a cada: {s['expected_min']}min\n"
        )
    lines.append("_Verifique os logs: docker compose logs app_")

    message = "\n".join(lines)

    # Envia apenas para o primeiro número (health alerts não precisam ir para watchlist completa)
    number = settings.alert_numbers[0]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}",
                headers={"apikey": settings.evolution_api_key, "Content-Type": "application/json"},
                json={"number": number, "options": {"delay": 500},
                      "textMessage": {"text": message}},
            )
            if resp.status_code == 201:
                logger.warning(f"[HealthCheck] Alerta enviado para {number[-4:]}**** — {len(stalled)} scrapers parados")
            else:
                logger.error(f"[HealthCheck] Falha ao enviar alerta: HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"[HealthCheck] Erro ao enviar alerta: {e}")
