"""
BaseScraper — motor base para todos os scrapers.
Correções aplicadas:
- BUG 5: removido import desnecessário de SessionLocal dentro de run()
- Adicionado: disparo de alerta WhatsApp para campanhas novas (BUG 10)
"""
import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from miles_radar.logger import logger
from miles_radar.settings import settings

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]


class ScrapedItem:
    def __init__(self, title: str, url: str, source_name: str, raw_text: str,
                 published_at: Optional[datetime] = None, extra: dict = None):
        self.title = title
        self.url = url
        self.source_name = source_name
        self.raw_text = raw_text
        # FIX BUG 3: normaliza timezone para naive UTC aqui na origem
        if published_at and published_at.tzinfo is not None:
            published_at = published_at.replace(tzinfo=None)
        self.published_at = published_at
        self.extra = extra or {}

    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.source_name}|{self.url}|{self.title}".encode()).hexdigest()


class BaseScraper(ABC):
    name: str = "base"
    base_url: str = ""
    interval_minutes: int = 30

    def __init__(self):
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    async def _get_browser_context(self, playwright):
        user_agent = random.choice(USER_AGENTS)
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                     "--disable-blink-features=AutomationControlled"],
        }
        if settings.use_proxy and settings.proxy_url:
            launch_kwargs["proxy"] = {"server": settings.proxy_url}
        browser = await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        return browser, context

    async def _jitter_sleep(self, base_seconds: float = 2.0):
        await asyncio.sleep(base_seconds * random.uniform(0.8, 1.2))

    async def _safe_get_page(self, context, url: str, wait_for: str = None):
        page = await context.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
        except Exception as e:
            try:
                screenshot_path = self.screenshots_dir / f"{self.name}_{int(time.time())}.png"
                await page.screenshot(path=str(screenshot_path))
            except Exception:
                pass
            raise e
        return page

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def fetch_with_retry(self, url: str, wait_for: str = None) -> str:
        async with async_playwright() as playwright:
            browser, context = await self._get_browser_context(playwright)
            try:
                page = await self._safe_get_page(context, url, wait_for)
                await self._jitter_sleep(1.5)
                return await page.content()
            finally:
                await browser.close()

    @abstractmethod
    async def scrape(self) -> List[ScrapedItem]:
        pass

    async def run(self, db_session, is_bootstrap: bool = False) -> dict:
        """Executa scraper, salva campanhas novas e dispara alertas WhatsApp."""
        from miles_radar.models.campaign import ScrapeRun, Campaign
        from miles_radar.parsers.campaign_parser import CampaignParser

        started = datetime.utcnow()
        run = ScrapeRun(source_name=self.name, is_bootstrap=is_bootstrap)
        db_session.add(run)
        db_session.commit()

        logger.info(f"[{self.name}] Iniciando {'bootstrap' if is_bootstrap else 'monitor'}")

        try:
            items = await self.scrape()
            # Usa LLM parser (v2) que faz fallback para v1 internamente
            try:
                from miles_radar.parsers.llm_parser import LLMParser
                parser = LLMParser()
            except ImportError:
                parser = CampaignParser()
            new_count = 0
            new_campaigns = []

            for item in items:
                campaign = parser.parse(item)
                if campaign:
                    existing = db_session.query(Campaign).filter(
                        Campaign.content_hash == campaign.content_hash
                    ).first()
                    if not existing:
                        db_session.add(campaign)
                        db_session.flush()  # gera ID sem commit
                        new_campaigns.append(campaign)
                        new_count += 1

            db_session.commit()

            # FIX BUG 10: dispara alertas para campanhas novas (não bootstrap)
            if not is_bootstrap and new_campaigns:
                await self._fire_alerts(new_campaigns, db_session)

            elapsed = (datetime.utcnow() - started).total_seconds()
            run.finished_at = datetime.utcnow()
            run.duration_seconds = elapsed
            run.campaigns_found = len(items)
            run.campaigns_new = new_count
            run.status = "success"
            db_session.commit()

            logger.success(f"[{self.name}] OK em {elapsed:.1f}s — {len(items)} encontrados, {new_count} novos")
            return {"status": "success", "found": len(items), "new": new_count}

        except Exception as e:
            elapsed = (datetime.utcnow() - started).total_seconds()
            run.finished_at = datetime.utcnow()
            run.duration_seconds = elapsed
            run.status = "error"
            run.error_message = str(e)[:500]
            db_session.commit()
            logger.error(f"[{self.name}] Erro após {elapsed:.1f}s: {e}")
            return {"status": "error", "error": str(e)}

    async def _fire_alerts(self, campaigns, db_session):
        """Dispara alertas WhatsApp para campanhas novas (global + watchlist individual)."""
        from miles_radar.notifier.whatsapp import send_alert, send_watchlist_alerts
        for campaign in campaigns:
            try:
                await send_alert(campaign, db_session=db_session)
                await send_watchlist_alerts(campaign, db_session=db_session)
            except Exception as e:
                logger.warning(f"[{self.name}] Alerta WhatsApp falhou: {e}")
