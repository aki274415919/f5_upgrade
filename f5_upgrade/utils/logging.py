import logging
from datetime import datetime
from pathlib import Path

def setup_logging(level="INFO", log_dir="reports"):
    """Setup unified logging to console and file.

    Args:
        level (str): logging level name.
        log_dir (str): directory to store log file.

    Returns:
        tuple: (logger instance, log_file path)
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"run_{ts}.log"
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    # clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger, str(log_file)
