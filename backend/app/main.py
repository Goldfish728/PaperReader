from fastapi import FastAPI

from backend.app.api.settings import router as settings_router
from backend.app.db.engine import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="PaperReader", version="0.1.0")
    app.include_router(settings_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
