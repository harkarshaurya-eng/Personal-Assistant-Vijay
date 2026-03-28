from __future__ import annotations

import uvicorn

from backend.app import create_app
from core.config_store import ConfigStore

app = create_app()


def main() -> None:
    settings = ConfigStore().load_settings()
    uvicorn.run(
        "main:app",
        host=settings.get("host", "127.0.0.1"),
        port=int(settings.get("port", 8000)),
        reload=False,
    )


if __name__ == "__main__":
    main()

