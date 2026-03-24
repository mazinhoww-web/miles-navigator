from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from miles_radar.models.database import Base


class Campaign(Base):
    """Cada promoção de milhas detectada."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    # Hash para deduplicação
    content_hash = Column(String(64), unique=True, index=True)

    # Identificação
    title = Column(String(500))
    source_name = Column(String(100), index=True)   # "passageirodeprimeira", "smiles", etc.
    source_url = Column(String(1000))
    promo_url = Column(String(1000))                # Link direto para participar

    # Classificação
    promo_type = Column(String(50), index=True)     # transfer_bonus, direct_purchase, club_combo, flash_sale
    origin_program = Column(String(100), index=True)
    destination_program = Column(String(100), index=True)

    # Período
    reference_month = Column(String(7), index=True) # "2026-03"
    starts_at = Column(DateTime(timezone=True))
    ends_at = Column(DateTime(timezone=True))
    duration_days = Column(Float)
    is_flash = Column(Boolean, default=False)        # Duração < 24h

    # Bônus resumido (tier base, para filtros rápidos)
    bonus_pct_base = Column(Float)
    bonus_pct_max = Column(Float)

    # Limites
    min_transfer = Column(Integer)
    max_transfer = Column(Integer)
    max_bonus_miles = Column(Integer)

    # VPP calculado
    cpm_estimated = Column(Float)                   # R$/1k milhas (tier base)
    cpm_min = Column(Float)                         # R$/1k milhas (tier máximo)
    vpp_real_base = Column(Float)
    vpp_real_clube = Column(Float)
    vpp_real_elite = Column(Float)

    # Empilhamento
    stackable_with = Column(JSON, default=list)
    not_stackable_with = Column(JSON, default=list)

    # Metadados
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True))
    raw_text = Column(Text)
    confidence_score = Column(Float, default=0.0)
    extraction_method = Column(String(10), default="regex")  # "regex" ou "llm"
    also_covered_by = Column(JSON, default=list)

    # Relacionamentos
    bonus_tiers = relationship("BonusTier", back_populates="campaign", cascade="all, delete-orphan")
    loyalty_tiers = relationship("LoyaltyDurationTier", back_populates="campaign", cascade="all, delete-orphan")


class BonusTier(Base):
    """Camada de bônus por perfil de cliente em uma campanha."""
    __tablename__ = "bonus_tiers"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), index=True)

    tier_name = Column(String(100))       # "Base", "Clube Pass", "Clube + Cartão Itaú", "Diamante"
    bonus_pct = Column(Float)
    condition = Column(String(500))       # Descrição da condição
    requires_club = Column(Boolean, default=False)
    club_name = Column(String(100))
    requires_card = Column(Boolean, default=False)
    card_name = Column(String(100))
    requires_category = Column(String(50))  # "Diamante", "Ouro", etc.
    sort_order = Column(Integer, default=0)

    campaign = relationship("Campaign", back_populates="bonus_tiers")


class LoyaltyDurationTier(Base):
    """Bônus extra por tempo de clube (específico Azul Fidelidade e similares)."""
    __tablename__ = "loyalty_duration_tiers"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), index=True)

    min_months = Column(Integer)    # A partir de X meses
    max_months = Column(Integer)    # Até Y meses (null = sem limite)
    bonus_pct_extra = Column(Float)
    label = Column(String(200))     # "Clube Azul 5 anos+"
    max_bonus_limit = Column(Integer)  # Limite de pontos bônus neste tier

    campaign = relationship("Campaign", back_populates="loyalty_tiers")


class ScrapeRun(Base):
    """Log de cada execução de scraper."""
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    source_name = Column(String(100), index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    campaigns_found = Column(Integer, default=0)
    campaigns_new = Column(Integer, default=0)
    status = Column(String(20), default="running")  # running, success, error
    error_message = Column(Text)
    is_bootstrap = Column(Boolean, default=False)


class AlertLog(Base):
    """Registro de cada alerta WhatsApp enviado."""
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    recipient_number = Column(String(20))
    message_preview = Column(String(200))
    status = Column(String(20))   # sent, failed
    error = Column(Text)


class BootstrapState(Base):
    """Controle do progresso do bootstrap histórico por fonte."""
    __tablename__ = "bootstrap_state"

    id = Column(Integer, primary_key=True)
    source_name = Column(String(100), unique=True)
    oldest_month_collected = Column(String(7))   # "2023-03" — mês mais antigo já coletado
    total_pages_scraped = Column(Integer, default=0)
    total_campaigns_found = Column(Integer, default=0)
    is_complete = Column(Boolean, default=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())


class VppReference(Base):
    """
    Valores-alvo de VPP extraídos dos blogs (Melhores Destinos, PP).
    Alimenta o motor VPP da Fase 4.
    """
    __tablename__ = "vpp_references"

    id = Column(Integer, primary_key=True)
    program = Column(String(100), index=True)       # "Smiles", "Pass", "Azul Fidelidade"
    reference_date = Column(DateTime(timezone=False), index=True)
    vpp_perceived = Column(Float)                   # R$/1k milhas — valor-alvo publicado
    source_blog = Column(String(100))
    source_url = Column(String(1000))
    raw_excerpt = Column(Text)                      # Trecho original que originou o valor
    created_at = Column(DateTime(timezone=False), server_default=func.now())
