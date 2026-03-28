from __future__ import annotations

import socket

import uvicorn

from backend.app import create_app
from core.config_store import ConfigStore

app = create_app()


def resolve_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred_port))
            return preferred_port
        except OSError:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])


def main() -> None:
    settings = ConfigStore().load_settings()
    host = str(settings.get("host", "127.0.0.1"))
    preferred_port = int(settings.get("port", 8000))
    port = resolve_port(host, preferred_port)
    if port != preferred_port:
        print(
            f"Configured port {preferred_port} is busy. Vijay is starting on http://{host}:{port} instead."
        )
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
