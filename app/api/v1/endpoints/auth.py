"""Authentication endpoints with comprehensive error handling."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.api.deps import get_db
from app.core.exceptions import (
    ConflictException,
    UnauthorizedException,
    InternalServerException,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.token import Token
from app.core.security import create_access_token
from app.api.v1.responses import (
    responses_401_409_500,
    responses_401_500,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Daftar Akun Baru",
    tags=["auth"],
    responses={
        **responses_401_409_500(),
        422: {
            "description": "Unprocessable Entity - Validation error (Pydantic validation failed)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Validasi data gagal.",
                        "details": {"field_errors": [{"field": "email", "message": "field required"}]},
                        "timestamp": "2026-06-10T12:00:00Z"
                    }
                }
            }
        },
    },
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register new user account.
    
    Error handling:
    - 409 Conflict: Email already registered
    - 422 Validation Error: Invalid input data
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_email = result.scalar_one_or_none()
    
    if existing_email:
        logger.warning(f"Registration failed: email '{user_data.email}' already registered")
        raise ConflictException(
            message="Email sudah terdaftar. Silakan gunakan email lain.",
            existing_resource=f"Email: {user_data.email}"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )
    
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"User registered successfully: {new_user.email}")
        
        return new_user
    except Exception as exc:
        await db.rollback()
        logger.error(f"Registration failed: {exc}", exc_info=True)
        raise InternalServerException("Gagal membuat akun. Silakan coba lagi.")


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Token untuk Swagger UI Authorize",
    tags=["auth"],
)
async def oauth2_login(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 password flow untuk Swagger UI Authorize.
    """
    # Find user by email (username in OAuth2 flow)
    result = await db.execute(
        select(User).where(User.email == username)
    )
    user = result.scalar_one_or_none()
    
    # Security: Use same error message for both email not found and wrong password
    if user is None or not verify_password(password, user.hashed_password):
        logger.warning(f"OAuth2 login failed for email: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not user.is_active:
        logger.warning(f"OAuth2 login failed: account inactive for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun tidak aktif.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    try:
        access_token = create_access_token(subject=str(user.id))
        logger.info(f"OAuth2 token created for user: {user.email}")
        return Token(access_token=access_token, token_type="bearer")
    except Exception as exc:
        logger.error(f"OAuth2 token creation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membuat token.",
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login dan Dapatkan JWT Token",
    tags=["auth"],
    responses={
        **responses_401_500(),
        422: {
            "description": "Unprocessable Entity - Validation error (Pydantic validation failed)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Validasi data gagal.",
                        "details": {"field_errors": [{"field": "email", "message": "field required"}]},
                        "timestamp": "2026-06-10T12:00:00Z"
                    }
                }
            }
        },
    },
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT access token.
    
    Error handling:
    - 401 Unauthorized: Invalid email or password
    - 403 Forbidden: Account not active
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Security: Use same error message for both email not found and wrong password
    # This prevents user enumeration attacks
    if user is None or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed for email: {credentials.email}")
        raise UnauthorizedException("Email atau password salah.")
    
    # Check if account is active
    if not user.is_active:
        logger.warning(f"Login failed: account inactive for user {user.id}")
        raise UnauthorizedException("Akun tidak aktif. Silakan hubungi admin.")
    
    # Create access token
    try:
        access_token = create_access_token(subject=str(user.id))
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return Token(access_token=access_token, token_type="bearer")
    except Exception as exc:
        logger.error(f"Token creation failed: {exc}", exc_info=True)
        raise InternalServerException("Gagal membuat token. Silakan coba lagi.")