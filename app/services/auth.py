from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User

# ─── Setup ────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ALGORITHM = "HS256"


# ─── Password ─────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Ubah password plain text jadi hash yang aman disimpan di DB."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Cek apakah password yang diketik cocok dengan hash di DB."""
    return pwd_context.verify(plain, hashed)


# ─── JWT Token ────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Buat JWT token.
    JWT itu seperti kartu akses yang berisi:
    - Siapa pemegangnya (user_id, email, role)
    - Kapan kadaluarsa
    - Tanda tangan digital (tidak bisa dipalsukan)
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


# ─── Get Current User ─────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency FastAPI — otomatis dipanggil di setiap endpoint yang butuh login.
    Baca token dari header, validasi, return user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kadaluarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_loan_officer(current_user: User = Depends(get_current_user)) -> User:
    """Hanya loan officer & admin yang boleh akses."""
    if current_user.role not in ("loan_officer", "admin"):
        raise HTTPException(status_code=403, detail="Akses ditolak — hanya untuk loan officer")
    return current_user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Hanya admin yang boleh akses."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses ditolak — hanya untuk admin")
    return current_user