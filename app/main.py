from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.config import settings
from app.database import async_engine, Base
import app.models  # noqa: F401 — register semua models ke Base


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — buat semua tabel di database
    print(f"🚀 Starting {settings.app_name} [{settings.app_env}]")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    print("👋 Shutting down...")
    await async_engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Explainable AI Credit Decisioning — XGBoost + SHAP + Gemini Flash + RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Rate Limiter ─────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────
from app.api import auth
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "env": settings.app_env,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}