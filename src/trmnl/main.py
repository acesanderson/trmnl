import uvicorn
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main():
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
