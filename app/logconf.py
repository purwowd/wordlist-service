import logging

LOG_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"

def setup(level: str = "INFO") -> None:
    logging.basicConfig(level=logging.getLevelName(level.upper()),
                        format=LOG_FMT)
    # prevent double-printing from uvicorn’s default handlers
    logging.getLogger("uvicorn.error").propagate = False
    logging.getLogger("uvicorn.access").propagate = False
