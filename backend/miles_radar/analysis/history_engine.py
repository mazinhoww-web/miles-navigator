"""
Motor de análise histórica — Fase 3.

PONTO CENTRAL: os dados históricos NÃO dependem de tempo corrido.
Os blogs de milhas têm arquivo de posts desde 2014.
O bootstrap já coletou esses posts e os salvou no banco com `published_at`
refletindo a data real da publicação.

Portanto, ao calcular "últimos 12 meses", filtramos por published_at >= (hoje - 12 meses),
que pode incluir dados históricos coletados no bootstrap — não apenas dados coletados
depois que o sistema subiu.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from miles_radar.models.campaign import Campaign, BonusTier
from miles_radar.logger import logger


# Janelas de análise disponíveis (em meses)
WINDOWS = [3, 6, 12, 18, 24, 36]

# VPP percebido de referência (Melhores Destinos, dez/2025)
VPP_TARGETS = {
    "Smiles": 16.00,
    "Pass": 25.00,
    "Azul Fidelidade": 14.00,
}


def get_window_start(months: int) -> datetime:
    """Retorna o início da janela temporal baseado em published_at."""
    return datetime.utcnow() - timedelta(days=months * 30)


def compute_route_history(
    db: Session,
    origin: Optional[str],
    destination: Optional[str],
    months: int,
) -> dict:
    """
    Calcula todas as métricas históricas para uma rota (origin → destination)
    na janela temporal especificada.

    Filtra por published_at (data real da publicação do post),
    não por detected_at (data em que o scraper rodou).
    Isso garante que dados históricos do bootstrap sejam aproveitados imediatamente.
    """
    since = get_window_start(months)

    # Base query
    q = db.query(Campaign).filter(
        Campaign.published_at >= since,
        Campaign.bonus_pct_max.isnot(None),
    )
    if origin:
        q = q.filter(Campaign.origin_program.ilike(f"%{origin}%"))
    if destination:
        q = q.filter(Campaign.destination_program.ilike(f"%{destination}%"))

    campaigns = q.order_by(Campaign.published_at).all()

    if not campaigns:
        return _empty_result(origin, destination, months)

    # ── Métricas básicas ──────────────────────────────────────────────
    bonus_base_vals = [c.bonus_pct_base for c in campaigns if c.bonus_pct_base]
    bonus_max_vals  = [c.bonus_pct_max  for c in campaigns if c.bonus_pct_max]
    cpm_vals        = [c.cpm_min for c in campaigns if c.cpm_min]
    duration_vals   = [c.duration_days for c in campaigns if c.duration_days and c.duration_days > 0]

    avg_bonus_base = _avg(bonus_base_vals)
    avg_bonus_max  = _avg(bonus_max_vals)
    max_bonus_ever = max(bonus_max_vals, default=0)
    min_cpm_ever   = min(cpm_vals, default=None)
    avg_cpm        = _avg(cpm_vals)
    avg_duration   = _avg(duration_vals)

    # ── Frequência por mês ────────────────────────────────────────────
    frequency_per_month = round(len(campaigns) / months, 2)

    # ── Tendência do bônus (regressão linear simples) ─────────────────
    trend_bonus = _linear_trend(bonus_max_vals) if len(bonus_max_vals) >= 3 else 0.0

    # ── Sazonalidade — índice por mês do calendário ───────────────────
    seasonality = _compute_seasonality(campaigns)
    best_calendar_month = max(seasonality, key=lambda x: x["index"])["month"] if seasonality else None

    # ── Intervalo entre campanhas → estimativa da próxima ─────────────
    interval_stats = _compute_intervals(campaigns)
    days_since_last = _days_since_last(campaigns)
    expected_next = _estimate_next(days_since_last, interval_stats)

    # ── Flash sales e exigência de clube ─────────────────────────────
    flash_count = sum(1 for c in campaigns if c.is_flash)
    flash_rate  = round(flash_count / len(campaigns), 3) if campaigns else 0
    club_count  = sum(1 for c in campaigns if _requires_club(c))
    club_rate   = round(club_count / len(campaigns), 3) if campaigns else 0

    # ── Série temporal mensal (para gráfico de evolução) ─────────────
    monthly_series = _monthly_series(campaigns, months)

    # ── Distribuição de duração ────────────────────────────────────────
    duration_dist = _duration_distribution(duration_vals)

    return {
        "origin": origin,
        "destination": destination,
        "window_months": months,
        "window_start": since.strftime("%Y-%m-%d"),
        "total_campaigns": len(campaigns),
        "frequency_per_month": frequency_per_month,
        "avg_duration_days": round(avg_duration, 1) if avg_duration else None,
        "avg_bonus_base": round(avg_bonus_base, 1) if avg_bonus_base else None,
        "avg_bonus_max": round(avg_bonus_max, 1) if avg_bonus_max else None,
        "max_bonus_ever": max_bonus_ever,
        "min_cpm_ever": round(min_cpm_ever, 2) if min_cpm_ever else None,
        "avg_cpm": round(avg_cpm, 2) if avg_cpm else None,
        "trend_bonus": round(trend_bonus, 3),
        "trend_direction": "subindo" if trend_bonus > 0.5 else "caindo" if trend_bonus < -0.5 else "estável",
        "seasonality": seasonality,
        "best_calendar_month": best_calendar_month,
        "days_since_last": days_since_last,
        "interval_median_days": interval_stats.get("median"),
        "interval_p25_days": interval_stats.get("p25"),
        "interval_p75_days": interval_stats.get("p75"),
        "expected_next_days": expected_next,
        "flash_rate": flash_rate,
        "club_required_rate": club_rate,
        "monthly_series": monthly_series,
        "duration_distribution": duration_dist,
        "vpp_target": VPP_TARGETS.get(destination),
    }


def compute_all_programs_summary(db: Session, months: int) -> list:
    """
    Resumo de todos os programas-destino na janela dada.
    Usado para rankings e comparativos.
    """
    since = get_window_start(months)
    rows = (
        db.query(
            Campaign.destination_program,
            func.count(Campaign.id).label("count"),
            func.avg(Campaign.bonus_pct_max).label("avg_bonus"),
            func.max(Campaign.bonus_pct_max).label("max_bonus"),
            func.avg(Campaign.cpm_min).label("avg_cpm"),
            func.min(Campaign.cpm_min).label("min_cpm"),
            func.sum(func.cast(Campaign.is_flash, func.Integer() if False else Campaign.id.__class__)).label("flash_count"),
        )
        .filter(Campaign.published_at >= since, Campaign.destination_program.isnot(None))
        .group_by(Campaign.destination_program)
        .order_by(desc("avg_bonus"))
        .all()
    )

    result = []
    for r in rows:
        result.append({
            "program": r.destination_program,
            "count": r.count,
            "avg_bonus": round(float(r.avg_bonus), 1) if r.avg_bonus else 0,
            "max_bonus": float(r.max_bonus) if r.max_bonus else 0,
            "avg_cpm": round(float(r.avg_cpm), 2) if r.avg_cpm else None,
            "min_cpm": round(float(r.min_cpm), 2) if r.min_cpm else None,
            "vpp_target": VPP_TARGETS.get(r.destination_program),
        })
    return result


def compute_seasonality_heatmap(db: Session, months: int) -> list:
    """
    Heatmap de sazonalidade: para cada programa × mês do calendário,
    retorna o bônus médio histórico.
    """
    since = get_window_start(months)
    campaigns = db.query(Campaign).filter(
        Campaign.published_at >= since,
        Campaign.bonus_pct_max.isnot(None),
        Campaign.destination_program.isnot(None),
    ).all()

    # Agrupa por programa × mês
    data: dict = {}
    for c in campaigns:
        if not c.published_at:
            continue
        prog = c.destination_program
        cal_month = c.published_at.month
        key = (prog, cal_month)
        if key not in data:
            data[key] = []
        data[key].append(c.bonus_pct_max)

    result = []
    MONTH_NAMES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    programs = sorted(set(k[0] for k in data))
    for prog in programs:
        row = {"program": prog, "months": []}
        for m in range(1, 13):
            vals = data.get((prog, m), [])
            row["months"].append({
                "month": m,
                "month_name": MONTH_NAMES[m-1],
                "avg_bonus": round(_avg(vals), 1) if vals else 0,
                "count": len(vals),
            })
        result.append(row)
    return result


# ── Helpers internos ──────────────────────────────────────────────────────────

def _avg(vals: list) -> Optional[float]:
    return sum(vals) / len(vals) if vals else None


def _linear_trend(vals: list) -> float:
    """Coeficiente angular da regressão linear (slope). Positivo = subindo."""
    n = len(vals)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(vals) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, vals))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


def _compute_seasonality(campaigns: list) -> list:
    """Índice de sazonalidade por mês do calendário (1.0 = média histórica)."""
    by_month: dict = {m: [] for m in range(1, 13)}
    for c in campaigns:
        if c.published_at:
            by_month[c.published_at.month].append(c.bonus_pct_max or 0)

    overall_avg = _avg([v for vals in by_month.values() for v in vals]) or 1
    MONTH_NAMES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    result = []
    for m in range(1, 13):
        vals = by_month[m]
        avg = _avg(vals) or 0
        index = round(avg / overall_avg, 2) if overall_avg else 0
        result.append({
            "month": m,
            "month_name": MONTH_NAMES[m-1],
            "avg_bonus": round(avg, 1),
            "count": len(vals),
            "index": index,
        })
    return result


def _compute_intervals(campaigns: list) -> dict:
    """Calcula estatísticas dos intervalos entre campanhas consecutivas."""
    dates = sorted([c.published_at for c in campaigns if c.published_at])
    if len(dates) < 2:
        return {}
    intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    intervals.sort()
    n = len(intervals)
    return {
        "median": intervals[n // 2],
        "p25": intervals[n // 4],
        "p75": intervals[n * 3 // 4],
        "mean": round(sum(intervals) / n, 1),
        "all": intervals,
    }


def _days_since_last(campaigns: list) -> Optional[int]:
    dates = [c.published_at for c in campaigns if c.published_at]
    if not dates:
        return None
    last = max(dates)
    return (datetime.utcnow() - last).days


def _estimate_next(days_since: Optional[int], interval_stats: dict) -> Optional[int]:
    """Estima em quantos dias a próxima campanha deve aparecer."""
    if not days_since or not interval_stats.get("median"):
        return None
    median = interval_stats["median"]
    remaining = median - days_since
    return max(0, remaining)


def _monthly_series(campaigns: list, months: int) -> list:
    """Série temporal: bônus máximo por mês para o gráfico de evolução."""
    by_month: dict = {}
    for c in campaigns:
        if c.published_at and c.bonus_pct_max:
            key = c.published_at.strftime("%Y-%m")
            if key not in by_month or c.bonus_pct_max > by_month[key]["max_bonus"]:
                by_month[key] = {
                    "month": key,
                    "max_bonus": c.bonus_pct_max,
                    "avg_bonus": 0,
                    "count": 0,
                }

    # Calcula médias
    month_vals: dict = {}
    for c in campaigns:
        if c.published_at and c.bonus_pct_max:
            key = c.published_at.strftime("%Y-%m")
            month_vals.setdefault(key, []).append(c.bonus_pct_max)
    for key, vals in month_vals.items():
        if key in by_month:
            by_month[key]["avg_bonus"] = round(_avg(vals), 1)
            by_month[key]["count"] = len(vals)

    return sorted(by_month.values(), key=lambda x: x["month"])


def _duration_distribution(duration_vals: list) -> dict:
    """Classifica campanhas por faixa de duração."""
    buckets = {"flash_lt24h": 0, "d1_3": 0, "d4_7": 0, "d8_15": 0, "d15_plus": 0}
    for d in duration_vals:
        if d < 1: buckets["flash_lt24h"] += 1
        elif d <= 3: buckets["d1_3"] += 1
        elif d <= 7: buckets["d4_7"] += 1
        elif d <= 15: buckets["d8_15"] += 1
        else: buckets["d15_plus"] += 1
    total = sum(buckets.values()) or 1
    return {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in buckets.items()}


def _requires_club(campaign) -> bool:
    return any(t.requires_club for t in campaign.bonus_tiers) if campaign.bonus_tiers else False


def _empty_result(origin, destination, months) -> dict:
    return {
        "origin": origin, "destination": destination, "window_months": months,
        "total_campaigns": 0, "frequency_per_month": 0, "avg_bonus_max": None,
        "max_bonus_ever": 0, "min_cpm_ever": None, "trend_direction": "estável",
        "seasonality": [], "days_since_last": None, "expected_next_days": None,
        "flash_rate": 0, "club_required_rate": 0, "monthly_series": [],
        "duration_distribution": {}, "vpp_target": VPP_TARGETS.get(destination),
    }
