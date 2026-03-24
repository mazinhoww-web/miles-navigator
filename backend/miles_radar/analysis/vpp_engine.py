"""
Motor VPP — Fase 4.

Calcula e historifica o Valor Por Ponto (VPP) de cada campanha.

Terminologia correta para apresentação executiva:
  - VPP Real:      custo efetivo (R$/1k milhas) para adquirir via uma ação
  - Valor-alvo:    preço máximo considerado "bom negócio" (referência Melhores Destinos)
  - Economia/1k:   valor-alvo − VPP real (positivo = vantajoso)
  - Classificação: EXCELENTE (>R$5), BOM (R$1–5), NEUTRO (<R$1), AGUARDAR (negativo)
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from miles_radar.models.campaign import Campaign, BonusTier, VppReference
from miles_radar.logger import logger

# ── Valores-alvo de referência (Melhores Destinos, dez/2025) ─────────────────
VPP_TARGETS: dict[str, float] = {
    "Smiles": 16.00,
    "LATAM Pass": 25.00,
    "Azul Fidelidade": 14.00,
}

# ── CPM de origem em promoção (custo por 1.000 pontos) ───────────────────────
# Usado como base de cálculo quando a campanha é de transferência bonificada.
# Representa o custo de COMPRAR pontos Livelo em promoção (58% de desconto).
CPM_ORIGINS: dict[str, float] = {
    "Livelo": 29.50,       # compra direta em promo 58% desc
    "Esfera": 30.00,       # estimativa (Santander, sem compra direta frequente)
    "Iupp Itaú": 0.0,      # pontos orgânicos — custo depende do gasto do cliente
    "Nubank Rewards": 0.0,
    "C6 Átomos": 0.0,
    "Inter Loop": 0.0,
    "Sicoob": 0.0,
    "Caixa Econômica": 0.0,
}

CPM_LIVELO_FALLBACK = 29.50  # usado quando origem não tem CPM cadastrado


def cpm_for_origin(origin: Optional[str]) -> Optional[float]:
    """Retorna o CPM de compra de pontos para a origem dada."""
    if not origin:
        return CPM_LIVELO_FALLBACK
    cpm = CPM_ORIGINS.get(origin)
    # 0.0 significa "pontos orgânicos" — não calculável via compra
    if cpm == 0.0:
        return None
    return cpm or CPM_LIVELO_FALLBACK


def calc_vpp_real(bonus_pct: float, cpm_origin: float, parity: float = 1.0) -> float:
    """
    VPP Real = (CPM_origem × paridade) / (1 + bônus/100)
    Paridade = quantos pontos de origem para 1 milha de destino (1:1 para Livelo→aéreos BR)
    """
    if bonus_pct <= 0 or cpm_origin <= 0:
        return 0.0
    return round((cpm_origin * parity) / (1 + bonus_pct / 100), 2)


def classify_opportunity(economy_per_k: float) -> str:
    if economy_per_k > 5.0:
        return "EXCELENTE"
    elif economy_per_k > 1.0:
        return "BOM"
    elif economy_per_k > 0:
        return "NEUTRO"
    return "AGUARDAR"


def enrich_campaign_vpp(campaign: Campaign) -> dict:
    """
    Calcula os valores de VPP para todos os tiers de uma campanha.
    Retorna dict pronto para serialização na API e no WhatsApp.
    """
    vpp_target = VPP_TARGETS.get(campaign.destination_program)
    cpm_origin = cpm_for_origin(campaign.origin_program)
    profiles = []

    for tier in sorted(campaign.bonus_tiers, key=lambda t: t.sort_order or 0):
        if not tier.bonus_pct:
            continue
        if cpm_origin:
            vpp_real = calc_vpp_real(tier.bonus_pct, cpm_origin)
            economy = round(vpp_target - vpp_real, 2) if vpp_target else None
            classification = classify_opportunity(economy) if economy is not None else "NEUTRO"
        else:
            vpp_real = None
            economy = None
            classification = "NEUTRO"

        profiles.append({
            "tier_name": tier.tier_name,
            "bonus_pct": tier.bonus_pct,
            "vpp_real": vpp_real,
            "vpp_target": vpp_target,
            "economy_per_k": economy,
            "economy_pct": round(economy / vpp_target * 100, 1) if economy and vpp_target else None,
            "classification": classification,
            "requires_club": tier.requires_club,
            "requires_card": tier.requires_card,
            "requires_category": tier.requires_category,
            "club_name": tier.club_name,
        })

    # Atualiza campos de VPP na campanha (best tier)
    if profiles and cpm_origin:
        best = max(profiles, key=lambda p: p["economy_per_k"] or -99)
        worst = min(profiles, key=lambda p: p["vpp_real"] or 999)
        campaign.vpp_real_base = profiles[0]["vpp_real"] if profiles else None
        campaign.vpp_real_clube = next(
            (p["vpp_real"] for p in profiles if p.get("requires_club")), None
        )
        campaign.vpp_real_elite = worst["vpp_real"]
        campaign.cpm_min = worst["vpp_real"]

    return {
        "destination": campaign.destination_program,
        "origin": campaign.origin_program,
        "cpm_origin_used": cpm_origin,
        "vpp_target": vpp_target,
        "profiles": profiles,
        "best_economy": max((p["economy_per_k"] for p in profiles if p["economy_per_k"] is not None), default=None),
        "best_classification": profiles[-1]["classification"] if profiles else "NEUTRO",
    }


# ── Análise histórica de VPP ──────────────────────────────────────────────────

def compute_vpp_history(db: Session, destination: Optional[str], months: int) -> dict:
    """
    Métricas históricas de VPP para um programa-destino na janela dada.
    Inclui tendência (subindo=piorando, caindo=melhorando) e volatilidade.
    """
    since = datetime.utcnow() - timedelta(days=months * 30)

    q = db.query(Campaign).filter(
        Campaign.published_at >= since,
        Campaign.cpm_min.isnot(None),
    )
    if destination:
        q = q.filter(Campaign.destination_program == destination)

    campaigns = q.order_by(Campaign.published_at).all()

    if not campaigns:
        return {"destination": destination, "months": months, "total": 0, "profiles": []}

    vpp_vals = [c.cpm_min for c in campaigns if c.cpm_min]
    vpp_target = VPP_TARGETS.get(destination) if destination else None

    # Volatilidade = desvio padrão
    volatility = None
    if len(vpp_vals) >= 2:
        mean = sum(vpp_vals) / len(vpp_vals)
        variance = sum((x - mean) ** 2 for x in vpp_vals) / len(vpp_vals)
        volatility = round(variance ** 0.5, 2)

    # Tendência linear (slope)
    trend = _linear_slope(vpp_vals)
    trend_dir = "subindo" if trend > 0.05 else "caindo" if trend < -0.05 else "estável"
    # Para VPP: subindo = piorando (mais caro), caindo = melhorando (mais barato)
    trend_meaning = "piorando" if trend > 0.05 else "melhorando" if trend < -0.05 else "estável"

    # Série mensal
    monthly: dict = {}
    for c in campaigns:
        if c.published_at and c.cpm_min:
            key = c.published_at.strftime("%Y-%m")
            monthly.setdefault(key, []).append(c.cpm_min)
    series = [
        {"month": k, "avg_vpp": round(sum(v)/len(v), 2), "count": len(v)}
        for k, v in sorted(monthly.items())
    ]

    # Ranking de ações por melhor VPP (menor = melhor)
    best_actions = []
    seen = set()
    for c in sorted(campaigns, key=lambda x: x.cpm_min or 999):
        key = f"{c.origin_program}→{c.destination_program}"
        if key in seen:
            continue
        seen.add(key)
        economy = round(vpp_target - c.cpm_min, 2) if vpp_target and c.cpm_min else None
        best_actions.append({
            "route": key,
            "origin": c.origin_program,
            "destination": c.destination_program,
            "best_bonus": c.bonus_pct_max,
            "vpp_real": c.cpm_min,
            "vpp_target": vpp_target,
            "economy_per_k": economy,
            "classification": classify_opportunity(economy) if economy else "NEUTRO",
            "campaign_id": c.id,
            "title": c.title,
            "ends_at": c.ends_at.isoformat() if c.ends_at else None,
        })

    return {
        "destination": destination,
        "months": months,
        "total": len(campaigns),
        "vpp_avg": round(sum(vpp_vals)/len(vpp_vals), 2) if vpp_vals else None,
        "vpp_min": round(min(vpp_vals), 2) if vpp_vals else None,
        "vpp_max": round(max(vpp_vals), 2) if vpp_vals else None,
        "vpp_target": vpp_target,
        "volatility": volatility,
        "trend_slope": round(trend, 4),
        "trend_direction": trend_dir,
        "trend_meaning": trend_meaning,
        "monthly_series": series,
        "best_actions": best_actions[:8],
    }


def compute_vpp_all_programs(db: Session, months: int) -> list:
    """Resumo de VPP para todos os programas na janela dada."""
    results = []
    for prog in ["Smiles", "LATAM Pass", "Azul Fidelidade"]:
        data = compute_vpp_history(db, destination=prog, months=months)
        results.append(data)
    return sorted(results, key=lambda x: x.get("vpp_min") or 999)


def extract_vpp_references_from_text(text: str, source: str, url: str, pub_date: datetime) -> list:
    """
    Extrai referências de valor-alvo de posts de análise dos blogs.
    Chamado pelo scraper do Melhores Destinos quando detecta padrão de CPM.
    Retorna lista de VppReference prontos para salvar no banco.
    """
    import re
    refs = []

    # Padrões de extração de valor-alvo
    patterns = [
        (r'valor[- ]alvo[^\d]{0,15}R?\$?\s*([\d,\.]+)', None),
        (r'bom negócio[^\d]{0,10}R?\$?\s*([\d,\.]+)', None),
        (r'R?\$?\s*([\d,\.]+)\s*(?:o?\s*milh[eê]iro|por\s+mil(?:has)?)', None),
        (r'CPM[^\d]{0,8}R?\$?\s*([\d,\.]+)', None),
    ]

    # Detecta o programa ao qual o valor se refere
    t_lower = text.lower()
    program_map = {
        "smiles": "Smiles",
        "latam pass": "LATAM Pass",
        "latam": "LATAM Pass",
        "azul fidelidade": "Azul Fidelidade",
        "azul": "Azul Fidelidade",
    }

    program = None
    for alias, canonical in program_map.items():
        if alias in t_lower:
            program = canonical
            break

    if not program:
        return refs

    for pattern, _ in patterns:
        for m in re.finditer(pattern, text, re.I):
            try:
                val = float(m.group(1).replace(",", "."))
                if 8.0 <= val <= 50.0:  # range razoável para CPM em BRL
                    refs.append(VppReference(
                        program=program,
                        reference_date=pub_date,
                        vpp_perceived=val,
                        source_blog=source,
                        source_url=url,
                        raw_excerpt=text[max(0, m.start()-50):m.end()+50],
                    ))
                    break  # 1 referência por padrão
            except (ValueError, AttributeError):
                continue

    return refs


def _linear_slope(vals: list) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx, my = sum(xs)/n, sum(vals)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,vals))
    den = sum((x-mx)**2 for x in xs)
    return num/den if den else 0.0
