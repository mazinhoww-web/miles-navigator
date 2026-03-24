from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    # Banco de dados
    database_url: str = Field(
        default="sqlite:///./milesradar.db",
        env="DATABASE_URL"
    )

    # Evolution API / WhatsApp
    evolution_api_url: str = Field(default="http://evolution:8080", env="EVOLUTION_API_URL")
    evolution_api_key: str = Field(default="change-me", env="EVOLUTION_API_KEY")
    evolution_instance: str = Field(default="milesradar", env="EVOLUTION_INSTANCE")

    # Alertas
    alert_numbers_raw: str = Field(default="", env="ALERT_NUMBERS")
    min_bonus_pct: float = Field(default=40.0, env="MIN_BONUS_PCT")
    programs_watch_raw: str = Field(default="", env="PROGRAMS_WATCH")
    max_cpm: float = Field(default=20.0, env="MAX_CPM")
    silent_start_hour: int = Field(default=23, env="SILENT_START_HOUR")
    silent_end_hour: int = Field(default=7, env="SILENT_END_HOUR")

    # Scraping
    bootstrap_months: int = Field(default=36, env="BOOTSTRAP_MONTHS")
    bootstrap_delay_seconds: float = Field(default=3.0, env="BOOTSTRAP_DELAY_SECONDS")
    use_proxy: bool = Field(default=False, env="USE_PROXY")
    proxy_url: Optional[str] = Field(default=None, env="PROXY_URL")

    # Apify — scraping via cloud actors
    apify_token: str = Field(default="", env="APIFY_TOKEN")
    apify_actor_passageirodeprimeira: str = Field(default="", env="APIFY_ACTOR_PASSAGEIRODEPRIMEIRA")
    apify_actor_melhoresdestinos: str = Field(default="", env="APIFY_ACTOR_MELHORESDESTINOS")
    apify_actor_mestredasmilhas: str = Field(default="", env="APIFY_ACTOR_MESTREDASMILHAS")
    apify_actor_pontospravoar: str = Field(default="", env="APIFY_ACTOR_PONTOSPRAVOAR")
    apify_actor_smiles: str = Field(default="", env="APIFY_ACTOR_SMILES")
    apify_actor_latampass: str = Field(default="", env="APIFY_ACTOR_LATAMPASS")
    apify_actor_azul: str = Field(default="", env="APIFY_ACTOR_AZUL")
    apify_actor_livelo: str = Field(default="", env="APIFY_ACTOR_LIVELO")
    apify_actor_esfera: str = Field(default="", env="APIFY_ACTOR_ESFERA")
    apify_actor_itau_iupp: str = Field(default="", env="APIFY_ACTOR_ITAU_IUPP")
    apify_actor_nubank: str = Field(default="", env="APIFY_ACTOR_NUBANK")
    apify_actor_c6: str = Field(default="", env="APIFY_ACTOR_C6")
    apify_actor_inter: str = Field(default="", env="APIFY_ACTOR_INTER")
    apify_actor_sicoob: str = Field(default="", env="APIFY_ACTOR_SICOOB")

    # Parser LLM (Fase 6)
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    llm_confidence_threshold: float = Field(default=0.7, env="LLM_CONFIDENCE_THRESHOLD")
    llm_enabled: bool = Field(default=True, env="LLM_ENABLED")

    # App
    environment: str = Field(default="prod", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    @property
    def alert_numbers(self) -> List[str]:
        if not self.alert_numbers_raw:
            return []
        return [n.strip() for n in self.alert_numbers_raw.split(",") if n.strip()]

    @property
    def programs_watch(self) -> List[str]:
        if not self.programs_watch_raw:
            return []
        return [p.strip() for p in self.programs_watch_raw.split(",") if p.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
