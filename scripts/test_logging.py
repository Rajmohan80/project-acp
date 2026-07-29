"""Quick validation — Block 6 logging check."""
from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger

get_settings()
configure_logging()
log = get_logger("test")
log.info("block6_test", status="ok", phase=0)