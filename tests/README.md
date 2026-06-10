# Testing Documentation

## Overview

This project includes a comprehensive automated testing infrastructure using pytest, pytest-asyncio, and pytest-cov.

## Testing Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner and assertion library |
| `pytest-asyncio` | Async test support for FastAPI |
| `httpx` AsyncClient | HTTP client for API testing |
| `pytest-cov` | Coverage reporting |
| `pytest-mock` | Mocking utilities |
| `faker` | Test data generation |
| `aiosqlite` | In-memory SQLite for async testing |

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── pytest.ini                  # Pytest configuration
├── utils.py                   # Test utilities and factories
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py        # Model unit tests
│   └── test_schemas.py       # Schema unit tests
└── integration/
    ├── __init__.py
    ├── test_auth.py           # Authentication integration tests
    └── test_jobs.py           # Jobs/drafts/history integration tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock faker aiosqlite httpx
```

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Run with HTML Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html:htmlcov
```

### Run Specific Test Category

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

## Test Fixtures

### conftest.py Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_session` | function | Async database session with auto-rollback |
| `client` | function | AsyncClient for API testing |
| `authenticated_client` | function | Client with Bearer token |
| `test_user` | function | Test user in database |
| `other_user` | function | Another test user for authorization tests |
| `test_user_data` | function | Random test user data |
| `test_image` | function | Test image bytes |
| `fake` | function | Faker instance for Indonesian locale |

## Test Categories

### Unit Tests

- `tests/unit/test_models.py` - Database model tests
- `tests/unit/test_schemas.py` - Pydantic schema validation tests

### Integration Tests

- `tests/integration/test_auth.py` - Authentication flow tests
- `tests/integration/test_jobs.py` - Jobs, drafts, history, and sharing tests

## Coverage Targets

| Component | Target Coverage |
|-----------|-----------------|
| Models | 90% |
| Schemas | 95% |
| Services | 80% |
| API Endpoints | 85% |
| **Overall** | **80% minimum** |

## CI/CD Integration

The project includes GitHub Actions workflow for automated testing:

- **Location**: `.github/workflows/test.yml`
- **Trigger**: Push to main/develop, Pull requests
- **Coverage**: Codecov integration
- **Threshold**: Fails if coverage drops below 80%

## Writing Tests

### Example: Unit Test

```python
import pytest
from app.models.user import User

class TestUserModel:
    def test_user_default_values(self, test_user: User):
        """Test user has correct default values."""
        assert test_user.is_active is True
        assert test_user.is_verified is False
```

### Example: Integration Test

```python
import pytest
from httpx import AsyncClient

class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(
        self, client: AsyncClient, test_user: User, test_user_data: dict
    ):
        """Test successful login returns 200."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
```

### Example: Authorization Test

```python
@pytest.mark.asyncio
async def test_get_draft_other_user(
    self,
    authenticated_client: AsyncClient,
    db_session,
    other_user: User,
):
    """Test getting another user's draft returns 403."""
    # Create draft owned by other_user
    check = LokerCheck(user_id=other_user.id, job_title="Other's Draft", is_draft=True)
    db_session.add(check)
    await db_session.commit()
    await db_session.refresh(check)

    # Try to access with authenticated_client (different user)
    response = await authenticated_client.get(f"/api/v1/jobs/drafts/{check.id}")
    assert response.status_code == 403