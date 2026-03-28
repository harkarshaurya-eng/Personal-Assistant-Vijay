from __future__ import annotations

import logging
from pathlib import Path


def get_logger() -> logging.Logger:
    logger = logging.getLogger("vijay")
    if logger.handlers:
        return logger

    log_path = Path(__file__).resolve().parent.parent / "data" / "vijay.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

