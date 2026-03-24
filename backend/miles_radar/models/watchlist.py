"""
Watchlist — múltiplos destinatários com filtros individuais por número (Fase 6).
Cada número pode ter seus próprios filtros de programa, bônus mínimo e CPM máximo.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from miles_radar.models.database import Base


class WatchlistEntry(Base):
    """Entrada da watchlist: número WhatsApp + filtros de alerta personalizados."""
    __tablename__ = "watchlist_entries"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), nullable=False, index=True)
    destination_program = Column(String(100))      # null = todos
    origin_program = Column(String(100))           # null = todos
    min_bonus_pct = Column(Float, default=40.0)
    max_cpm = Column(Float, default=20.0)
    flash_only = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_alerted_at = Column(DateTime)
    alert_count = Column(Integer, default=0)
    label = Column(String(100))                    # nome amigável para o usuário
