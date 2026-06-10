"""Test configuration and shared fixtures for CekLoker Backend API."""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from faker import Faker
from passlib.context import CryptContext

from app.main import app
from app.api.deps import get_db
from app.models.base import Base
from app.core.security import create_access_token

# Import all models to ensure Base.metadata includes all tables
from app.models.user import User
from app.models.loker_check import LokerCheck

# Test database configuration - uses file-based SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash password for test fixtures."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password for test fixtures."""
    return pwd_context.verify(plain_password, hashed_password)


# ========== Session Fixtures ==========

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session scope."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create async test database engine with schema creation/teardown."""
    # Remove existing test database if it exists
    if os.path.exists("test.db"):
        os.remove("test.db")
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
    
    # Clean up test database
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session with automatic rollback after each test."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


# ========== HTTP Client Fixtures ==========
@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing with database override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def authenticated_client(
    client: AsyncClient,
    test_user
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated HTTP client with Bearer token."""
    token = create_access_token(subject=str(test_user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


# ========== Data Fixtures ==========
@pytest.fixture
def fake() -> Faker:
    """Create Faker instance for Indonesian locale test data generation."""
    return Faker("id_ID")


@pytest.fixture
def test_user_data(fake: Faker) -> dict:
    """Generate random test user data."""
    return {
        "email": fake.unique.email(),
        "password": "TestPassword123!",
        "full_name": fake.name(),
    }


@pytest.fixture
def other_user_data(fake: Faker) -> dict:
    """Generate another random user data for authorization tests."""
    return {
        "email": fake.unique.email(),
        "password": "OtherPassword123!",
        "full_name": fake.name(),
    }


@pytest.fixture
async def test_user(db_session: AsyncSession, test_user_data: dict):
    """Create test user in database with hashed password."""
    user = User(
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        full_name=test_user_data["full_name"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession, other_user_data: dict):
    """Create another test user for authorization tests."""
    user = User(
        email=other_user_data["email"],
        hashed_password=get_password_hash(other_user_data["password"]),
        full_name=other_user_data["full_name"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ========== Test Data Fixtures ==========
@pytest.fixture
def test_image() -> bytes:
    """Generate test image bytes (800x600 JPEG)."""
    from tests.utils import generate_test_image
    return generate_test_image()


@pytest.fixture
def valid_ocr_data() -> dict:
    """Generate valid OCR data for testing."""
    return {
        "job_title": "Software Engineer",
        "job_type": "Full-time",
        "company_name": "PT Contoh Indonesia",
        "company_email": "hr@contoh.co.id",
        "phone_number": "081234567890",
        "salary": "Rp 5.000.000 - 8.000.000",
        "description": "Lowongan pekerjaan untuk fresh graduate",
    }


@pytest.fixture
def suspicious_ocr_data() -> dict:
    """Generate suspicious OCR data for scam analysis testing."""
    return {
        "job_title": "Kerja dari Rumah",
        "job_type": "Freelance",
        "company_name": "KlikDisini.com",
        "company_email": "online@job4u.xyz",
        "phone_number": "085211112222",
        "salary": "Rp 15.000.000 - 50.000.000",
        "description": "Tanpa interview, langsung kerja!",
    }