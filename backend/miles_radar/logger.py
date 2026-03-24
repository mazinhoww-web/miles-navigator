import sys
from loguru import logger
from miles_radar.settings import settings

# Remove o handler padrão
logger.remove()

if settings.is_dev:
    # Dev: colorido e legível no terminal
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
else:
    # Produção: JSON estruturado em arquivo
    logger.add(
        "logs/miles_radar.log",
        format="{time} | {level} | {name} | {message}",
        level=settings.log_level,
        rotation="50 MB",
        retention="30 days",
        compression="gz",
        serialize=True,  # JSON
    )
    # Também no terminal em prod (sem cor)
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
        level="WARNING",
    )
