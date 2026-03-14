"""Root launcher for local development.

Allows running the service with:
python main.py
"""

from app.config import get_config


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("app.main:app", host=config.app_host, port=config.app_port, reload=False)
