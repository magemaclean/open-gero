from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .db import SessionLocal, init_db
from .routers import admin, auth, chem, datasets, exports, jobs, molecules, projects, search, targets
from .seed import seed_all

DISCLAIMER = (
    "OpenGero is a research tool for computational hypothesis generation. "
    "It does not provide medical advice, diagnose disease, or recommend human dosing. "
    "Docking scores and similarity ranks are prioritization heuristics, not experimental measurements."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OpenGero API",
        version=__version__,
        description=DISCLAIMER,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def disclaimer_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-OpenGero-Disclaimer"] = "research-only-not-medical-advice"
        return response

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "disclaimer": DISCLAIMER,
        }

    @app.get("/api/meta")
    def meta():
        return {
            "name": "OpenGero",
            "version": __version__,
            "license": "Apache-2.0",
            "disclaimer": DISCLAIMER,
        }

    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(molecules.router)
    app.include_router(search.router)
    app.include_router(jobs.router)
    app.include_router(datasets.router)
    app.include_router(targets.router)
    app.include_router(exports.router)
    app.include_router(admin.router)
    app.include_router(chem.router)
    return app


app = create_app()
