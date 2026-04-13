import os
import socket
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import logging.config
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
EXPECTED_HOSTNAME = "caruana"


def main():
    if not os.getenv("TRMNL_SKIP_HOST_CHECK") and socket.gethostname() != EXPECTED_HOSTNAME:
        raise EnvironmentError(
            f"You are not on the trmnl server host (you should be on {EXPECTED_HOSTNAME})."
        )

    log_config = LOGGING_CONFIG.copy()
    log_config["loggers"]["trmnl"] = {
        "handlers": ["default"],  # same handler as uvicorn.error
        "level": "INFO",
        "propagate": False,
    }
    logging.config.dictConfig(log_config)
    uvicorn.run(
        "trmnl.app:app",
        host="0.0.0.0",
        port=8070,
        reload=True,
        reload_dirs=[str(BASE_DIR)],
        log_level="info",
    )


if __name__ == "__main__":
    main()
