import logging
import os

log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
numeric_log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=numeric_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(numeric_log_level)
logger.setLevel(numeric_log_level)

def get_logger(nome: str) -> logging.Logger:
    """Logger filho (arcos.<nome>) que herda formato e nível do basicConfig acima."""
    return logging.getLogger(f"arcos.{nome}")
