"""
Parser v1 — extrai campos estruturados de promoções a partir de texto bruto.
Correções aplicadas:
- BUG 8: _extract_dates data invertida corrigida (day/month/year)
- BUG 3: timezone-aware vs naive datetime unificado para UTC naive
- Limpeza de código morto (dateparser importado mas não usado)
"""
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from miles_radar.scrapers.base import ScrapedItem
from miles_radar.models.campaign import Campaign, BonusTier, LoyaltyDurationTier
from miles_radar.logger import logger

PROGRAM_ALIASES = {
    "smiles": "Smiles",
    "gol smiles": "Smiles",
    "pass": "Pass",
    "pass": "Pass",
    "azul fidelidade": "Azul Fidelidade",
    "tudoazul": "Azul Fidelidade",
    "tudo azul": "Azul Fidelidade",
    "livelo": "Livelo",
    "esfera": "Esfera",
    "iupp": "Iupp Itaú",
    "itaú": "Iupp Itaú",
    "nubank": "Nubank Rewards",
    "c6": "C6 Átomos",
    "átomos": "C6 Átomos",
    "inter": "Inter Loop",
    "sicoob": "Sicoob",
    "sicredi": "Sicredi",
    "caixa": "Caixa Econômica",
    "banco do brasil": "Banco do Brasil",
    "bradesco": "Bradesco",
    "santander": "Esfera",
}

PROMO_TYPE_KEYWORDS = {
    "transfer_bonus": ["transferência", "transferencia", "transferir", "bônus na transferência"],
    "direct_purchase": ["compra de milhas", "compra de pontos", "comprar milhas", "comprar pontos"],
    "club_signup": ["assine o clube", "adesão ao clube", "novo assinante", "assinar clube"],
    "club_combo": ["clube livelo", "clube smiles", "clube azul", "clube pass", "clube + transferência"],
    "flash_sale": ["só hoje", "somente hoje", "apenas hoje", "relâmpago", "flash"],
}

FLASH_KEYWORDS = ["só hoje", "somente hoje", "apenas hoje", "relâmpago", "flash",
                  "até às 23h59", "até 23h59 de hoje", "válido somente hoje"]

DEST_PROGRAMS = {
    "smiles": "Smiles",
    "pass": "Pass",
    "pass": "Pass",
    "azul fidelidade": "Azul Fidelidade",
    "tudoazul": "Azul Fidelidade",
    "tudo azul": "Azul Fidelidade",
}


class CampaignParser:

    def parse(self, item: ScrapedItem) -> Optional[Campaign]:
        """Converte um ScrapedItem em um Campaign estruturado."""
        try:
            text = f"{item.title}\n{item.raw_text}".lower()
            original_text = f"{item.title}\n{item.raw_text}"

            if not self._is_miles_promo(text):
                return None

            origin = self._extract_origin(text)
            destination = self._extract_destination(text)

            if not destination:
                return None

            bonus_tiers = self._extract_bonus_tiers(text)
            bonus_base = bonus_tiers[0].bonus_pct if bonus_tiers else None
            bonus_max = max((t.bonus_pct for t in bonus_tiers), default=None)

            loyalty_tiers = self._extract_loyalty_tiers(text)
            promo_type = self._classify_promo_type(text)
            is_flash = self._detect_flash(text)

            # FIX BUG 3: normaliza published_at para timezone-naive UTC
            pub = item.published_at
            if pub and pub.tzinfo is not None:
                pub = pub.replace(tzinfo=None)

            starts_at, ends_at = self._extract_dates(text, pub)

            duration_days = None
            if starts_at and ends_at and ends_at > starts_at:
                duration_days = (ends_at - starts_at).total_seconds() / 86400

            reference_month = (pub or datetime.utcnow()).strftime("%Y-%m")

            confidence = self._calculate_confidence(
                origin, destination, bonus_base, starts_at, ends_at, bonus_tiers
            )

            content_hash = hashlib.sha256(
                f"{item.source_name}|{item.url}|{item.title}".encode()
            ).hexdigest()

            campaign = Campaign(
                content_hash=content_hash,
                title=item.title[:500],
                source_name=item.source_name,
                source_url=item.url,
                promo_url=item.url,
                promo_type=promo_type,
                origin_program=origin,
                destination_program=destination,
                reference_month=reference_month,
                starts_at=starts_at,
                ends_at=ends_at,
                duration_days=duration_days,
                is_flash=is_flash,
                bonus_pct_base=bonus_base,
                bonus_pct_max=bonus_max,
                published_at=pub,
                raw_text=original_text[:5000],
                confidence_score=confidence,
                extraction_method="regex",
                bonus_tiers=bonus_tiers,
                loyalty_tiers=loyalty_tiers,
            )
            return campaign

        except Exception as e:
            logger.debug(f"[Parser] Erro em '{item.title[:50]}': {e}")
            return None

    def _is_miles_promo(self, text: str) -> bool:
        kws = ["milhas", "pontos", "smiles", "pass", "azul fidelidade",
               "livelo", "esfera", "bônus", "bonus", "transferência", "transferencia"]
        return sum(1 for kw in kws if kw in text) >= 2

    def _extract_origin(self, text: str) -> Optional[str]:
        # Padrões explícitos: "pontos Livelo para Smiles"
        patterns = [
            r'(?:transfer[ie]r|enviar|mover)\s+pontos?\s+(?:do?a?\s+)?(\w[\w\s]+?)(?:\s+para|\s+ao|\s+à)',
            r'pontos?\s+(?:do?a?\s+)?(\w[\w\s]+?)\s+(?:para|ao|à)\s+(?:smiles|pass|azul)',
            r'(?:da?\s+)?(\w[\w\s]+?)\s+(?:para|ao|à)\s+(?:smiles|pass|azul)',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                candidate = m.group(1).strip().lower()
                for alias, canonical in PROGRAM_ALIASES.items():
                    if alias in candidate:
                        return canonical
        # Fallback por presença de nome de origem
        for alias in ["livelo", "esfera", "iupp", "nubank", "c6 ", "inter ", "itaú", "sicoob", "sicredi", "caixa"]:
            if alias in text:
                return PROGRAM_ALIASES.get(alias.strip(), alias.strip().title())
        return None

    def _extract_destination(self, text: str) -> Optional[str]:
        # Tenta programa mais específico primeiro (evita "pass" capturar onde deveria ser "pass")
        for alias in ["azul fidelidade", "tudoazul", "tudo azul", "pass", "smiles"]:
            if alias in text:
                return DEST_PROGRAMS[alias]
        # Fallback pass genérico
        if "pass" in text:
            return "Pass"
        return None

    def _extract_bonus_tiers(self, text: str) -> List[BonusTier]:
        tiers = []
        seen_pcts = set()

        # Extrai todos os valores de % de bônus com contexto adjacente
        matches = re.finditer(
            r'(\d+)%\s*(?:de\s+)?b[oô]nus([^\n]{0,120})',
            text, re.I
        )
        for i, m in enumerate(matches):
            try:
                pct = float(m.group(1))
                if pct in seen_pcts or pct > 500 or pct < 1:
                    continue
                seen_pcts.add(pct)
                context = m.group(2).lower() + text[max(0, m.start()-80):m.start()].lower()
                requires_club = any(kw in context for kw in ["clube", "assinante", "assinant", "plano"])
                requires_card = any(kw in context for kw in ["cartão", "cartao", "card"])
                requires_cat = "Diamante" if "diamante" in context else None

                # Nomeia o tier pelo contexto
                if i == 0 and not requires_club:
                    tier_name = "Base"
                elif "diamante" in context:
                    tier_name = "Diamante"
                elif requires_card:
                    tier_name = "Clube + Cartão"
                elif requires_club:
                    tier_name = "Clube"
                else:
                    tier_name = f"Tier {i+1}"

                tiers.append(BonusTier(
                    tier_name=tier_name,
                    bonus_pct=pct,
                    condition="",
                    requires_club=requires_club,
                    requires_card=requires_card,
                    requires_category=requires_cat,
                    sort_order=i,
                ))
            except ValueError:
                continue

        # Fallback se nenhum tier encontrado com "bônus"
        if not tiers:
            for i, m in enumerate(re.finditer(r'(\d+)%', text)):
                try:
                    pct = float(m.group(1))
                    if pct in seen_pcts or pct > 300 or pct < 5:
                        continue
                    seen_pcts.add(pct)
                    if len(tiers) >= 4:
                        break
                    tiers.append(BonusTier(
                        tier_name="Base" if i == 0 else f"Tier {i+1}",
                        bonus_pct=pct, condition="", sort_order=i,
                    ))
                except ValueError:
                    continue

        tiers.sort(key=lambda t: t.bonus_pct)
        for i, t in enumerate(tiers):
            t.sort_order = i
        return tiers

    def _extract_loyalty_tiers(self, text: str) -> List[LoyaltyDurationTier]:
        """Extrai loyalty tiers do Azul e similares."""
        tiers = []
        seen = set()
        # Padrão: "+10% de bônus – assinantes Clube Azul entre 1 a 2 anos"
        patterns = [
            r'\+(\d+)%[^\n]{0,60}?(\d+)\s*(?:a\s*\d+\s*)?(?:meses?|anos?)',
            r'(\d+)\s*meses?\s*[:\-–]\s*\+(\d+)%',
            r'(\d+)\s*anos?\s*[:\-–]\s*\+(\d+)%',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.I):
                try:
                    g = m.groups()
                    # Determina qual grupo é bônus e qual é tempo
                    try:
                        first, second = float(g[0]), float(g[1])
                    except (ValueError, IndexError):
                        continue
                    # Heurística: bônus <= 50, meses pode ser maior
                    if first <= 50 and second >= 1:
                        extra_pct, time_val = first, second
                    elif second <= 50 and first >= 1:
                        extra_pct, time_val = second, first
                    else:
                        continue
                    # Converte anos para meses
                    span = m.group(0).lower()
                    if "ano" in span and time_val <= 10:
                        time_val = int(time_val * 12)
                    else:
                        time_val = int(time_val)
                    key = (time_val, extra_pct)
                    if key not in seen and 0 < extra_pct <= 100 and time_val >= 1:
                        seen.add(key)
                        tiers.append(LoyaltyDurationTier(
                            min_months=time_val,
                            bonus_pct_extra=extra_pct,
                            label=f"{time_val}+ meses no clube",
                        ))
                except Exception:
                    continue
        tiers.sort(key=lambda t: t.min_months)
        return tiers

    def _classify_promo_type(self, text: str) -> str:
        for pt, kws in PROMO_TYPE_KEYWORDS.items():
            if any(kw in text for kw in kws):
                return pt
        if any(kw in text for kw in ["bônus", "bonus", "transferência", "transferencia"]):
            return "transfer_bonus"
        return "other"

    def _detect_flash(self, text: str) -> bool:
        return any(kw in text for kw in FLASH_KEYWORDS)

    def _extract_dates(self, text: str, published_at: Optional[datetime]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        FIX BUG 8: extração de datas corrigida.
        Padrão brasileiro: dia/mês/ano
        """
        starts_at = published_at or datetime.utcnow()
        # Remove tzinfo se presente (normaliza para naive UTC)
        if starts_at.tzinfo is not None:
            starts_at = starts_at.replace(tzinfo=None)
        ends_at = None

        now = datetime.utcnow()

        # Tenta extrair data de fim no formato DD/MM/AAAA ou DD/MM
        date_patterns = [
            # "até 23/03/2026" ou "válido até 23/03"
            r'(?:até|válido até|válida até|expira|termina)[^\d]{0,10}(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',
            # "até o dia 23" (sem mês — assume mês corrente/próximo)
            r'(?:até|válido até)[^\d]{0,10}(?:dia\s+)?(\d{1,2})(?:[/\-](\d{1,2}))?(?:[/\-](\d{2,4}))?',
        ]

        for pattern in date_patterns:
            m = re.search(pattern, text, re.I)
            if not m:
                continue
            try:
                groups = [g for g in m.groups() if g]
                if not groups:
                    continue

                day = int(groups[0])
                month = int(groups[1]) if len(groups) > 1 else (starts_at or now).month
                year_raw = int(groups[2]) if len(groups) > 2 else None

                # Valida ranges
                if not (1 <= day <= 31 and 1 <= month <= 12):
                    continue

                # Resolve ano
                if year_raw is None:
                    year = now.year
                    # Se a data já passou no ano corrente, assume próximo ano
                    try:
                        candidate = datetime(year, month, day)
                        if candidate < now - timedelta(days=1):
                            year += 1
                    except ValueError:
                        year = now.year
                elif year_raw < 100:
                    year = 2000 + year_raw
                else:
                    year = year_raw

                ends_at = datetime(year, month, day, 23, 59, 59)
                break
            except (ValueError, IndexError):
                continue

        # Estimativa quando não encontrou data
        if not ends_at and starts_at:
            is_flash = self._detect_flash(text)
            ends_at = starts_at + timedelta(hours=18 if is_flash else 7 * 24)

        return starts_at, ends_at

    def _calculate_confidence(self, origin, destination, bonus_base, starts_at, ends_at, bonus_tiers) -> float:
        score = 0.0
        if destination: score += 0.25
        if origin: score += 0.15
        if bonus_base: score += 0.20
        if starts_at: score += 0.10
        if ends_at: score += 0.10
        if len(bonus_tiers) > 1: score += 0.20
        return min(score, 1.0)
