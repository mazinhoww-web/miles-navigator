"""
Módulo de alertas WhatsApp via Evolution API.
"""
import httpx
from datetime import datetime, time
import pytz
from miles_radar.settings import settings
from miles_radar.logger import logger
from miles_radar.models.campaign import Campaign

BRT = pytz.timezone("America/Sao_Paulo")

PROMO_TYPE_LABELS = {
    "transfer_bonus": "Transferência Bonificada",
    "direct_purchase": "Compra Direta",
    "club_combo": "Combo Clube + Transferência",
    "club_signup": "Adesão ao Clube",
    "flash_sale": "Flash Sale",
    "other": "Promoção",
}

CLASSIFICATION_LABELS = {
    "EXCELENTE": "🟢 EXCELENTE",
    "BOM": "🔵 BOM",
    "NEUTRO": "⚪ NEUTRO",
    "AGUARDAR": "🔴 AGUARDAR",
}


def _is_silent_hours() -> bool:
    """Verifica se está no horário silencioso."""
    now_brt = datetime.now(BRT).time()
    start = time(settings.silent_start_hour, 0)
    end = time(settings.silent_end_hour, 0)
    if start > end:  # vira meia-noite
        return now_brt >= start or now_brt < end
    return start <= now_brt < end


def _should_alert(campaign: Campaign) -> bool:
    """Verifica se esta campanha deve gerar alerta."""
    if _is_silent_hours():
        logger.debug(f"[WhatsApp] Horário silencioso — pulando alerta para '{campaign.title[:40]}'")
        return False

    if campaign.bonus_pct_base and campaign.bonus_pct_base < settings.min_bonus_pct:
        logger.debug(f"[WhatsApp] Bônus {campaign.bonus_pct_base}% abaixo do mínimo {settings.min_bonus_pct}% — pulando")
        return False

    if settings.programs_watch and campaign.destination_program:
        if not any(p.lower() in campaign.destination_program.lower() for p in settings.programs_watch):
            logger.debug(f"[WhatsApp] Programa {campaign.destination_program} não está na watchlist — pulando")
            return False

    if campaign.cpm_min and campaign.cpm_min > settings.max_cpm:
        logger.debug(f"[WhatsApp] CPM R${campaign.cpm_min:.2f} acima do máximo R${settings.max_cpm:.2f} — pulando")
        return False

    return True


def _classify_opportunity(vpp_real: float, vpp_target: float) -> str:
    """Classifica a qualidade da oportunidade com base no spread."""
    if not vpp_real or not vpp_target:
        return "NEUTRO"
    economy = vpp_target - vpp_real
    if economy > 5.0:
        return "EXCELENTE"
    elif economy > 1.0:
        return "BOM"
    elif economy > 0:
        return "NEUTRO"
    return "AGUARDAR"


def _format_message(campaign: Campaign, historical_avg: float = None) -> str:
    """Formata a mensagem WhatsApp."""
    # VPP targets de referência (Melhores Destinos dez/2025)
    VPP_TARGETS = {
        "Smiles": 16.00,
        "Pass": 25.00,
        "Azul Fidelidade": 14.00,
    }

    vpp_target = VPP_TARGETS.get(campaign.destination_program)
    classification = _classify_opportunity(campaign.cpm_min, vpp_target) if vpp_target else "NEUTRO"

    promo_type_label = PROMO_TYPE_LABELS.get(campaign.promo_type, "Promoção")
    flash_tag = "⚡ *FLASH SALE*\n" if campaign.is_flash else ""

    # Cabeçalho
    lines = [
        flash_tag,
        f"🎯 *{campaign.destination_program or 'Milhas'}* — {promo_type_label}",
        "",
    ]

    # Rota
    if campaign.origin_program:
        lines.append(f"📤 *Origem:* {campaign.origin_program}")

    # Bônus
    if campaign.bonus_pct_base:
        bonus_line = f"📊 *Bônus base:* {campaign.bonus_pct_base:.0f}%"
        if campaign.bonus_pct_max and campaign.bonus_pct_max > campaign.bonus_pct_base:
            bonus_line += f"  |  *Máximo (clube):* {campaign.bonus_pct_max:.0f}%"
        lines.append(bonus_line)

    # VPP
    if campaign.cpm_min:
        lines.append(f"💰 *CPM estimado (tier máx):* R${campaign.cpm_min:.2f}/1k milhas")

    # Spread e classificação
    if vpp_target and campaign.cpm_min:
        economy = vpp_target - campaign.cpm_min
        class_label = CLASSIFICATION_LABELS.get(classification, "")
        if economy > 0:
            lines.append(f"{class_label} — economia de R${economy:.2f}/1k vs valor-alvo R${vpp_target:.2f}")
        else:
            lines.append(f"{class_label} — CPM acima do valor-alvo (R${vpp_target:.2f})")

    # Histórico
    if historical_avg and campaign.bonus_pct_max:
        diff = campaign.bonus_pct_max - historical_avg
        if abs(diff) > 5:
            direction = "acima" if diff > 0 else "abaixo"
            lines.append(f"📈 *Histórico:* {diff:+.0f}pp {direction} da média de 12m ({historical_avg:.0f}%)")

    # Validade
    if campaign.ends_at:
        ends_str = campaign.ends_at.astimezone(BRT).strftime("%d/%m às %H:%M")
        lines.append(f"⏰ *Válido até:* {ends_str} (horário de Brasília)")

    # Link
    if campaign.promo_url:
        lines.append(f"\n🔗 {campaign.promo_url}")

    # Rodapé
    lines.append(f"\n_Miles Radar · {datetime.now(BRT).strftime('%d/%m %H:%M')}_")

    return "\n".join(l for l in lines if l is not None)


async def send_alert(campaign: Campaign, db_session=None, historical_avg: float = None):
    """Envia alerta WhatsApp para todos os destinatários configurados."""
    if not _should_alert(campaign):
        return

    if not settings.alert_numbers:
        logger.warning("[WhatsApp] Nenhum número configurado em ALERT_NUMBERS")
        return

    message = _format_message(campaign, historical_avg)

    for number in settings.alert_numbers:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}",
                    headers={
                        "apikey": settings.evolution_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "number": number,
                        "options": {"delay": 1000},
                        "textMessage": {"text": message},
                    },
                )
                if response.status_code == 201:
                    logger.success(f"[WhatsApp] Alerta enviado para {number[-4:]}****")
                    if db_session:
                        from miles_radar.models.campaign import AlertLog
                        log = AlertLog(
                            campaign_id=campaign.id,
                            recipient_number=number,
                            message_preview=message[:200],
                            status="sent",
                        )
                        db_session.add(log)
                        db_session.commit()
                else:
                    logger.error(f"[WhatsApp] Erro HTTP {response.status_code} para {number}")

        except httpx.ConnectError:
            logger.warning("[WhatsApp] Evolution API não acessível — verifique se o container está rodando")
        except Exception as e:
            logger.error(f"[WhatsApp] Erro ao enviar para {number}: {e}")


async def send_watchlist_alerts(campaign: Campaign, db_session, historical_avg: float = None):
    """
    Fase 6: envia alertas para destinatários da watchlist com filtros individuais.
    Complementa o send_alert() global — não substitui.
    """
    if _is_silent_hours():
        return

    try:
        from miles_radar.models.watchlist import WatchlistEntry
        from datetime import timedelta
        from sqlalchemy import and_
    except ImportError:
        return

    entries = db_session.query(WatchlistEntry).filter(WatchlistEntry.active == True).all()
    if not entries:
        return

    for entry in entries:
        # Filtro de programa-destino
        if entry.destination_program and campaign.destination_program:
            if entry.destination_program.lower() not in campaign.destination_program.lower():
                continue

        # Filtro de origem
        if entry.origin_program and campaign.origin_program:
            if entry.origin_program.lower() not in campaign.origin_program.lower():
                continue

        # Filtro de bônus mínimo
        bonus = campaign.bonus_pct_base or 0
        if bonus < (entry.min_bonus_pct or 0):
            continue

        # Filtro de CPM máximo
        if entry.max_cpm and campaign.cpm_min and campaign.cpm_min > entry.max_cpm:
            continue

        # Filtro flash only
        if entry.flash_only and not campaign.is_flash:
            continue

        # Anti-spam: não renotifica em < 6 horas
        if entry.last_alerted_at:
            since = (datetime.utcnow() - entry.last_alerted_at).total_seconds() / 3600
            if since < 6:
                continue

        # Envia
        message = _format_message(campaign, historical_avg)
        label_suffix = f"\n_Alerta configurado: {entry.label}_" if entry.label else ""
        message = message + label_suffix

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}",
                    headers={"apikey": settings.evolution_api_key, "Content-Type": "application/json"},
                    json={"number": entry.phone_number, "options": {"delay": 1200},
                          "textMessage": {"text": message}},
                )
                if resp.status_code == 201:
                    entry.last_alerted_at = datetime.utcnow()
                    entry.alert_count = (entry.alert_count or 0) + 1
                    db_session.commit()
                    logger.success(f"[WhatsApp Watchlist] Alerta '{entry.label or entry.phone_number[-4:]}****' enviado")
        except Exception as e:
            logger.warning(f"[WhatsApp Watchlist] Erro para {entry.phone_number[-4:]}****: {e}")
