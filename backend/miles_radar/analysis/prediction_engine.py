"""
Motor de Previsão — Fase 5.

Estima probabilidade, timing e bônus esperado de campanhas futuras.

Abordagem estatística:
  - Intervalos históricos entre campanhas → distribuição empírica
  - Kaplan-Meier simplificado para P(campanha nos próximos N dias)
  - Ajuste por sazonalidade mensal
  - Calendário de eventos recorrentes (alta confiabilidade)
  - Estimativa de bônus por média ponderada com decaimento exponencial
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from miles_radar.models.campaign import Campaign
from miles_radar.logger import logger

# ── Calendário de eventos recorrentes ────────────────────────────────────────
# Confirmados por 3+ anos consecutivos. Alto impacto nas probabilidades.
CALENDAR_EVENTS = [
    {
        "name": "Aniversário Caixa Econômica (~165% bônus)",
        "month": 1, "day_start": 1, "day_end": 15,
        "programs": ["Pass", "Smiles", "Azul Fidelidade"],
        "expected_bonus": 165,
        "confidence": "MUITO ALTA",
        "multiplier": 3.0,
        "note": "Bônus histórico = idade do banco. Consistente há 4+ anos.",
    },
    {
        "name": "Dia do Consumidor",
        "month": 3, "day_start": 10, "day_end": 20,
        "programs": ["Pass", "Smiles", "Azul Fidelidade", "Livelo"],
        "expected_bonus": 80,
        "confidence": "ALTA",
        "multiplier": 2.0,
    },
    {
        "name": "Dia das Mães",
        "month": 5, "day_start": 5, "day_end": 12,
        "programs": ["Pass", "Smiles", "Azul Fidelidade"],
        "expected_bonus": 70,
        "confidence": "ALTA",
        "multiplier": 1.8,
    },
    {
        "name": "Aniversário Passageiro de Primeira (exclusivo Smiles)",
        "month": 7, "day_start": 9, "day_end": 15,
        "programs": ["Smiles"],
        "expected_bonus": 80,
        "confidence": "ALTA",
        "multiplier": 2.0,
    },
    {
        "name": "Aniversário Livelo (5/set)",
        "month": 9, "day_start": 1, "day_end": 10,
        "programs": ["Pass", "Smiles", "Azul Fidelidade"],
        "expected_bonus": 80,
        "confidence": "MUITO ALTA",
        "multiplier": 2.5,
    },
    {
        "name": "Aniversário Pass",
        "month": 9, "day_start": 10, "day_end": 25,
        "programs": ["Pass"],
        "expected_bonus": 50,
        "confidence": "MUITO ALTA",
        "multiplier": 2.5,
    },
    {
        "name": "Aniversário Azul Fidelidade",
        "month": 9, "day_start": 10, "day_end": 25,
        "programs": ["Azul Fidelidade"],
        "expected_bonus": 80,
        "confidence": "MUITO ALTA",
        "multiplier": 2.5,
    },
    {
        "name": "Aniversário Smiles / GOL",
        "month": 9, "day_start": 15, "day_end": 30,
        "programs": ["Smiles"],
        "expected_bonus": 100,
        "confidence": "MUITO ALTA",
        "multiplier": 2.5,
    },
    {
        "name": "Black Friday",
        "month": 11, "day_start": 20, "day_end": 30,
        "programs": ["Pass", "Smiles", "Azul Fidelidade", "Livelo"],
        "expected_bonus": 80,
        "confidence": "ALTA",
        "multiplier": 2.0,
    },
    {
        "name": "Natal / Réveillon",
        "month": 12, "day_start": 18, "day_end": 31,
        "programs": ["Pass", "Smiles", "Azul Fidelidade"],
        "expected_bonus": 60,
        "confidence": "ALTA",
        "multiplier": 1.8,
    },
]

URGENCY_LABELS = {
    "ACAO_IMINENTE": "Ação iminente",
    "ALTA_PROB": "Alta probabilidade",
    "MONITORAR": "Monitorar",
    "AGUARDAR": "Aguardar",
}


def predict_route(
    db: Session,
    origin: Optional[str],
    destination: Optional[str],
    horizon_days: int = 30,
) -> dict:
    """
    Previsão completa para uma rota.
    Retorna probabilidades em 7/15/30 dias + bônus esperado + urgência.
    """
    # Coleta histórico da rota
    campaigns = _get_route_campaigns(db, origin, destination, months=36)
    n = len(campaigns)

    if n == 0:
        return _empty_prediction(origin, destination)

    # Datas de publicação ordenadas
    dates = sorted([c.published_at for c in campaigns if c.published_at])
    intervals = _compute_intervals(dates)
    days_since_last = (datetime.utcnow() - max(dates)).days if dates else None

    # Probabilidades por horizonte
    p7  = _survival_probability(days_since_last, intervals, 7)
    p15 = _survival_probability(days_since_last, intervals, 15)
    p30 = _survival_probability(days_since_last, intervals, 30)

    # Ajuste por sazonalidade
    season_factor = _seasonality_factor(campaigns, datetime.utcnow().month)
    p7  = min(p7  * season_factor, 0.98)
    p15 = min(p15 * season_factor, 0.98)
    p30 = min(p30 * season_factor, 0.98)

    # Ajuste por evento do calendário
    active_events = _get_active_events(destination, horizon_days)
    if active_events:
        max_mult = max(e["multiplier"] for e in active_events)
        p7  = min(p7  * max_mult, 0.98)
        p15 = min(p15 * max_mult, 0.98)
        p30 = min(p30 * max_mult, 0.98)

    # Bônus esperado (média ponderada com decaimento exponencial)
    bonus_expected_base, bonus_expected_max, bonus_range = _expected_bonus(campaigns)

    # Duração esperada
    durations = [c.duration_days for c in campaigns if c.duration_days and 0 < c.duration_days < 60]
    duration_expected = round(sorted(durations)[len(durations)//2], 1) if durations else 3.0
    flash_prob = round(sum(1 for c in campaigns if c.is_flash) / n, 2) if n else 0

    # Confiança do modelo
    confidence, confidence_score = _model_confidence(n, intervals, active_events)

    # Urgência
    urgency = _classify_urgency(p7, p15, active_events)

    # Próxima data estimada
    median_interval = intervals.get("median", 21) if intervals else 21
    expected_next_date = None
    if days_since_last is not None:
        remaining = max(0, median_interval - days_since_last)
        expected_next_date = (datetime.utcnow() + timedelta(days=remaining)).strftime("%Y-%m-%d")

    # Evidências (frases explicativas)
    evidence = _build_evidence(n, days_since_last, intervals, season_factor, active_events, p7)

    return {
        "origin": origin,
        "destination": destination,
        "data_points": n,
        "prob_7d": round(p7, 3),
        "prob_15d": round(p15, 3),
        "prob_30d": round(p30, 3),
        "confidence": confidence,
        "confidence_score": round(confidence_score, 2),
        "days_since_last": days_since_last,
        "median_interval_days": intervals.get("median"),
        "expected_next_date": expected_next_date,
        "expected_next_days": max(0, (intervals.get("median", 21) or 21) - (days_since_last or 0)),
        "bonus_expected_base": bonus_expected_base,
        "bonus_expected_max": bonus_expected_max,
        "bonus_range_p25": bonus_range[0],
        "bonus_range_p75": bonus_range[1],
        "duration_expected_days": duration_expected,
        "flash_probability": flash_prob,
        "urgency": urgency,
        "urgency_label": URGENCY_LABELS[urgency],
        "active_calendar_events": active_events,
        "seasonality_factor": round(season_factor, 2),
        "evidence": evidence,
    }


def predict_all_routes(db: Session, horizon_days: int = 30) -> list:
    """Previsão para todas as rotas conhecidas, ordenadas por probabilidade."""
    routes = [
        ("Livelo", "Pass"),
        ("Livelo", "Smiles"),
        ("Livelo", "Azul Fidelidade"),
        ("Esfera", "Smiles"),
        ("Esfera", "Pass"),
        ("Esfera", "Azul Fidelidade"),
        ("Iupp Itaú", "Pass"),
        ("Iupp Itaú", "Smiles"),
        ("Nubank Rewards", "Smiles"),
        ("C6 Átomos", "Smiles"),
        ("Inter Loop", "Smiles"),
        (None, "Smiles"),       # qualquer origem → Smiles
        (None, "Pass"),   # qualquer origem → Pass
        (None, "Azul Fidelidade"),
    ]
    results = []
    for origin, dest in routes:
        pred = predict_route(db, origin, dest, horizon_days)
        if pred["data_points"] > 0 or pred["active_calendar_events"]:
            results.append(pred)

    # Remove duplicatas e ordena por prob_30d × confidence_score
    seen = set()
    unique = []
    for r in results:
        key = f"{r['origin']}→{r['destination']}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    unique.sort(key=lambda x: x["prob_30d"] * x["confidence_score"], reverse=True)
    return unique[:12]


def get_upcoming_events(days_ahead: int = 180) -> list:
    """Retorna eventos do calendário nos próximos N dias."""
    today = datetime.utcnow()
    upcoming = []

    for year_offset in [0, 1]:
        year = today.year + year_offset
        for event in CALENDAR_EVENTS:
            start = datetime(year, event["month"], event["day_start"])
            end = datetime(year, event["month"], event["day_end"])
            if start > today and (start - today).days <= days_ahead:
                upcoming.append({
                    **event,
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "days_until": (start - today).days,
                })

    upcoming.sort(key=lambda x: x["days_until"])
    return upcoming[:15]


# ── Funções internas ──────────────────────────────────────────────────────────

def _get_route_campaigns(db: Session, origin: Optional[str], destination: Optional[str], months: int):
    since = datetime.utcnow() - timedelta(days=months * 30)
    q = db.query(Campaign).filter(
        Campaign.published_at >= since,
        Campaign.published_at.isnot(None),
    )
    if destination:
        q = q.filter(Campaign.destination_program == destination)
    if origin:
        q = q.filter(Campaign.origin_program == origin)
    return q.order_by(Campaign.published_at).all()


def _compute_intervals(dates: list) -> dict:
    if len(dates) < 2:
        return {}
    intervals = sorted([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)])
    n = len(intervals)
    return {
        "all": intervals,
        "median": intervals[n // 2],
        "mean": round(sum(intervals) / n, 1),
        "p25": intervals[max(0, n // 4)],
        "p75": intervals[min(n-1, n * 3 // 4)],
        "p10": intervals[max(0, n // 10)],
        "p90": intervals[min(n-1, n * 9 // 10)],
        "std": round((_std(intervals)), 1),
    }


def _std(vals: list) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5


def _survival_probability(days_since: Optional[int], intervals: dict, horizon: int) -> float:
    """
    P(campanha nos próximos `horizon` dias | última há `days_since` dias).
    Baseado na fração histórica de intervalos que caem em [days_since, days_since+horizon].
    """
    if not intervals or not intervals.get("all") or days_since is None:
        # Sem dados: usa probabilidade base proporcional ao horizonte
        return min(horizon / 30 * 0.5, 0.9)

    all_intervals = intervals["all"]
    n = len(all_intervals)
    # Conta quantos intervalos cobrem o período [days_since, days_since+horizon]
    count = sum(1 for iv in all_intervals if days_since <= iv <= days_since + horizon)
    return min(count / n + 0.05, 0.98)  # +5% floor mínimo


def _seasonality_factor(campaigns: list, current_month: int) -> float:
    """Fator de ajuste sazonal: campanhas neste mês histórico vs média."""
    by_month = {m: 0 for m in range(1, 13)}
    for c in campaigns:
        if c.published_at:
            by_month[c.published_at.month] += 1
    total = sum(by_month.values())
    if total == 0:
        return 1.0
    monthly_avg = total / 12
    month_count = by_month[current_month]
    factor = (month_count / monthly_avg) if monthly_avg > 0 else 1.0
    return max(0.5, min(factor, 3.0))  # clipa entre 0.5× e 3×


def _get_active_events(destination: Optional[str], horizon_days: int) -> list:
    """Retorna eventos do calendário relevantes para o destino nos próximos horizon_days."""
    today = datetime.utcnow()
    active = []
    for year_offset in [0, 1]:
        year = today.year + year_offset
        for event in CALENDAR_EVENTS:
            if destination and destination not in event["programs"] and "Todos" not in event.get("programs", []):
                continue
            start = datetime(year, event["month"], event["day_start"])
            if 0 <= (start - today).days <= horizon_days:
                active.append({
                    **event,
                    "start_date": start.strftime("%Y-%m-%d"),
                    "days_until": (start - today).days,
                })
    return active


def _expected_bonus(campaigns: list) -> tuple:
    """Bônus esperado com decaimento exponencial (recente pesa mais)."""
    bonus_vals = [(c.bonus_pct_max, c.published_at) for c in campaigns
                  if c.bonus_pct_max and c.published_at]
    if not bonus_vals:
        return None, None, (None, None)

    bonus_vals.sort(key=lambda x: x[1])  # mais antigo primeiro
    n = len(bonus_vals)
    # Pesos decrescentes do mais antigo (0.5) ao mais recente (1.0)
    weights = [0.5 + 0.5 * i / max(n-1, 1) for i in range(n)]
    total_weight = sum(weights)
    weighted_avg = sum(b * w for (b, _), w in zip(bonus_vals, weights)) / total_weight

    vals_only = [b for b, _ in bonus_vals]
    vals_only.sort()
    p25 = vals_only[len(vals_only) // 4]
    p75 = vals_only[len(vals_only) * 3 // 4]

    base = min(vals_only)  # pior tier histórico como base
    return round(base, 0), round(weighted_avg, 0), (p25, p75)


def _model_confidence(n: int, intervals: dict, active_events: list) -> tuple:
    """Retorna (label, score 0–1)."""
    if active_events and any(e["confidence"] == "MUITO ALTA" for e in active_events):
        return "Muito Alta", 0.92
    if n >= 15 and intervals.get("std", 99) < 15:
        return "Alta", 0.82
    if n >= 8:
        return "Moderada", 0.65
    if n >= 3:
        return "Baixa", 0.45
    if active_events:
        return "Baseada em calendário", 0.70
    return "Muito Baixa", 0.25


def _classify_urgency(p7: float, p15: float, active_events: list) -> str:
    has_imminent_event = any(e.get("days_until", 99) <= 7 for e in active_events)
    if p7 > 0.70 and (has_imminent_event or p7 > 0.80):
        return "ACAO_IMINENTE"
    if p7 > 0.55 or p15 > 0.70:
        return "ALTA_PROB"
    if p15 > 0.40 or p7 > 0.35:
        return "MONITORAR"
    return "AGUARDAR"


def _build_evidence(n, days_since, intervals, season_factor, active_events, p7) -> list:
    ev = []
    if n > 0:
        ev.append(f"{n} campanhas na rota nos últimos 36 meses de histórico.")
    if days_since is not None and intervals.get("median"):
        ev.append(
            f"Última campanha há {days_since} dias. "
            f"Intervalo mediano histórico: {intervals['median']} dias."
        )
    if season_factor > 1.3:
        ev.append(f"Mês atual tem índice sazonal {season_factor:.1f}× acima da média histórica.")
    if active_events:
        for e in active_events[:2]:
            ev.append(f"Evento calendário: {e['name']} — começa em {e['days_until']} dias (confiança {e['confidence']}).")
    return ev


def _empty_prediction(origin, destination) -> dict:
    # Verifica se há evento de calendário mesmo sem dados históricos
    active_events = _get_active_events(destination, 30)
    urgency = "MONITORAR" if active_events else "AGUARDAR"
    return {
        "origin": origin,
        "destination": destination,
        "data_points": 0,
        "prob_7d": 0.0,
        "prob_15d": 0.0,
        "prob_30d": 0.0,
        "confidence": "Muito Baixa",
        "confidence_score": 0.1,
        "days_since_last": None,
        "median_interval_days": None,
        "expected_next_date": None,
        "expected_next_days": None,
        "bonus_expected_base": None,
        "bonus_expected_max": None,
        "bonus_range_p25": None,
        "bonus_range_p75": None,
        "duration_expected_days": 3.0,
        "flash_probability": 0.3,
        "urgency": urgency,
        "urgency_label": URGENCY_LABELS[urgency],
        "active_calendar_events": active_events,
        "seasonality_factor": 1.0,
        "evidence": ["Sem dados históricos para esta rota. Usando apenas calendário de eventos."],
    }
