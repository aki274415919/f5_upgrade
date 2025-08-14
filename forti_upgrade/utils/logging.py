import logging


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure root logger with a single console handler."""
    logger = logging.getLogger()
    if logger.handlers:
        return logger
    logger.setLevel(level)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger
