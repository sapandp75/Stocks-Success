from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.logging_config import setup_logging
from backend.database import init_db
from backend.routers import regime, screener, options, deep_dive, watchlist, positions, research

setup_logging()

app = FastAPI(title="Contrarian Investing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


app.include_router(regime.router)
app.include_router(screener.router)
app.include_router(options.router)
app.include_router(deep_dive.router)
app.include_router(watchlist.router)
app.include_router(positions.router)
app.include_router(research.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve React build (production mode)
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
