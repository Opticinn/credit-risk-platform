from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# ─── Sync engine (for Alembic migrations) ────────────────────
engine = create_engine(settings.database_url, echo=settings.app_env == "development")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ─── Async engine (for FastAPI routes) ───────────────────────
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.app_env == "development",
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# ─── Dependency ───────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
