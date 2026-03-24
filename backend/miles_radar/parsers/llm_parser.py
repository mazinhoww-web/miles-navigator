"""
Parser v2 — Claude API para posts com confidence_score abaixo do threshold.

Acionado automaticamente quando o parser v1 (regex) retorna confidence < 0.7.
Usa claude-sonnet-4-20250514 para extrair campos estruturados do texto bruto.
extraction_method = "llm" quando usado.

Custo estimado: ~R$0,05 por post ambíguo (input ~800 tokens + output ~200 tokens).
"""
import json
import httpx
from typing import Optional

from miles_radar.scrapers.base import ScrapedItem
from miles_radar.models.campaign import Campaign, BonusTier, LoyaltyDurationTier
from miles_radar.parsers.campaign_parser import CampaignParser
from miles_radar.settings import settings
from miles_radar.logger import logger

SYSTEM_PROMPT = """Você é um extrator especializado em promoções de milhas do mercado brasileiro.

Extraia os campos abaixo do texto de post/artigo fornecido e retorne APENAS um JSON válido, sem markdown, sem explicações.

Campos a extrair:
{
  "origin_program": "string ou null — programa de onde saem os pontos (Livelo, Esfera, Iupp Itaú, Nubank Rewards, C6 Átomos, Inter Loop, Sicoob, Caixa Econômica)",
  "destination_program": "string ou null — programa para onde vão as milhas (Smiles, Pass, Azul Fidelidade)",
  "promo_type": "transfer_bonus | direct_purchase | club_combo | club_signup | flash_sale | other",
  "is_flash": "boolean — true se duração < 24h ou palavras 'só hoje', 'relâmpago', 'somente hoje'",
  "bonus_tiers": [
    {
      "tier_name": "Base | Clube | Clube+Cartão | Diamante",
      "bonus_pct": "número float",
      "requires_club": "boolean",
      "requires_card": "boolean",
      "condition": "string curta descrevendo a condição"
    }
  ],
  "loyalty_tiers": [
    {
      "min_months": "inteiro — meses mínimos no clube",
      "bonus_pct_extra": "float — bônus adicional percentual",
      "label": "string — ex: '6+ meses no clube'"
    }
  ],
  "ends_at_text": "string ou null — data de validade como aparece no texto, ex: '31/03/2026'",
  "min_transfer": "inteiro ou null — mínimo de pontos para transferir",
  "confidence_score": "float 0.0-1.0 — sua confiança na extração"
}

Regras:
- Se não encontrar um campo, retorne null para strings ou [] para arrays
- bonus_pct deve ser o número puro (ex: 80 para 80%)
- Para Azul Fidelidade, procure os tiers de fidelidade (+5%, +10%, +20%, +30% por tempo no clube)
- Retorne SOMENTE o JSON, sem texto antes ou depois
"""


class LLMParser:
    """Parser v2 usando Claude API para extrair campos de posts ambíguos."""

    def __init__(self):
        self._v1 = CampaignParser()

    def should_use_llm(self, confidence: float) -> bool:
        """Decide se vale usar o LLM baseado no confidence score do parser v1."""
        if not settings.llm_enabled:
            return False
        if not settings.anthropic_api_key:
            return False
        return confidence < settings.llm_confidence_threshold

    def parse(self, item: ScrapedItem) -> Optional[Campaign]:
        """
        Estratégia em cascata:
        1. Tenta parser v1 (regex)
        2. Se confidence < threshold E LLM habilitado → tenta LLM
        3. Se LLM falhar → usa resultado do v1 mesmo com confidence baixa
        """
        campaign_v1 = self._v1.parse(item)

        if not self.should_use_llm(campaign_v1.confidence_score if campaign_v1 else 0.0):
            return campaign_v1

        logger.debug(
            f"[LLMParser] Acionando LLM para '{item.title[:50]}' "
            f"(confidence v1: {campaign_v1.confidence_score if campaign_v1 else 0:.2f})"
        )

        try:
            import asyncio
            llm_data = asyncio.get_event_loop().run_until_complete(
                self._call_claude(item.title, item.raw_text)
            )
            if llm_data:
                campaign_llm = self._build_campaign(item, llm_data)
                if campaign_llm and campaign_llm.confidence_score > (campaign_v1.confidence_score if campaign_v1 else 0):
                    campaign_llm.extraction_method = "llm"
                    logger.info(
                        f"[LLMParser] LLM melhorou confidence: "
                        f"{campaign_v1.confidence_score if campaign_v1 else 0:.2f} → {campaign_llm.confidence_score:.2f}"
                    )
                    return campaign_llm
        except Exception as e:
            logger.warning(f"[LLMParser] Falha na chamada LLM: {e} — usando resultado do parser v1")

        return campaign_v1

    async def _call_claude(self, title: str, raw_text: str) -> Optional[dict]:
        """Chama a Claude API e retorna o JSON extraído."""
        text_sample = f"TÍTULO: {title}\n\nCONTEÚDO:\n{raw_text[:3000]}"

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": text_sample}
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_json = data["content"][0]["text"].strip()
        # Remove markdown code blocks se presentes
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        return json.loads(raw_json)

    def _build_campaign(self, item: ScrapedItem, llm_data: dict) -> Optional[Campaign]:
        """Constrói um Campaign a partir do JSON retornado pelo LLM."""
        import hashlib
        from datetime import datetime, timedelta

        destination = llm_data.get("destination_program")
        if not destination:
            return None

        # Bonus tiers
        bonus_tiers = []
        for i, t in enumerate(llm_data.get("bonus_tiers") or []):
            try:
                bonus_tiers.append(BonusTier(
                    tier_name=t.get("tier_name", f"Tier {i+1}"),
                    bonus_pct=float(t["bonus_pct"]),
                    condition=t.get("condition", ""),
                    requires_club=t.get("requires_club", False),
                    requires_card=t.get("requires_card", False),
                    sort_order=i,
                ))
            except (KeyError, ValueError):
                continue
        bonus_tiers.sort(key=lambda x: x.bonus_pct)
        for i, t in enumerate(bonus_tiers):
            t.sort_order = i

        # Loyalty tiers
        loyalty_tiers = []
        for lt in llm_data.get("loyalty_tiers") or []:
            try:
                loyalty_tiers.append(LoyaltyDurationTier(
                    min_months=int(lt["min_months"]),
                    bonus_pct_extra=float(lt["bonus_pct_extra"]),
                    label=lt.get("label", ""),
                ))
            except (KeyError, ValueError):
                continue

        # Data de fim
        pub = item.published_at
        if pub and pub.tzinfo:
            pub = pub.replace(tzinfo=None)
        starts_at = pub or datetime.utcnow()
        ends_at = None
        ends_text = llm_data.get("ends_at_text")
        if ends_text:
            import re
            m = re.search(r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?', ends_text)
            if m:
                try:
                    day, month = int(m.group(1)), int(m.group(2))
                    yr = int(m.group(3)) if m.group(3) else datetime.utcnow().year
                    if yr < 100:
                        yr += 2000
                    ends_at = datetime(yr, month, day, 23, 59, 59)
                except ValueError:
                    pass
        if not ends_at:
            ends_at = starts_at + timedelta(hours=18 if llm_data.get("is_flash") else 168)

        bonus_base = bonus_tiers[0].bonus_pct if bonus_tiers else None
        bonus_max = max((t.bonus_pct for t in bonus_tiers), default=None)

        confidence = float(llm_data.get("confidence_score", 0.5))

        return Campaign(
            content_hash=hashlib.sha256(
                f"{item.source_name}|{item.url}|{item.title}".encode()
            ).hexdigest(),
            title=item.title[:500],
            source_name=item.source_name,
            source_url=item.url,
            promo_url=item.url,
            promo_type=llm_data.get("promo_type", "transfer_bonus"),
            origin_program=llm_data.get("origin_program"),
            destination_program=destination,
            reference_month=(pub or datetime.utcnow()).strftime("%Y-%m"),
            starts_at=starts_at,
            ends_at=ends_at,
            duration_days=(ends_at - starts_at).total_seconds() / 86400 if ends_at > starts_at else None,
            is_flash=bool(llm_data.get("is_flash", False)),
            bonus_pct_base=bonus_base,
            bonus_pct_max=bonus_max,
            min_transfer=llm_data.get("min_transfer"),
            published_at=pub,
            raw_text=item.raw_text[:5000],
            confidence_score=confidence,
            extraction_method="llm",
            bonus_tiers=bonus_tiers,
            loyalty_tiers=loyalty_tiers,
        )
