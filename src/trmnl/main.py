import uvicorn
from uvicorn.config import LOGGING_CONFIG
import logging.config
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def main():
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
