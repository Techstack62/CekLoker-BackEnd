"""Integration tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
from app.models.user import User


class TestAuthRegister:
    """Integration tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful user registration returns 201."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User, test_user_data: dict):
        """Test registration with duplicate email returns 409."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User, test_user_data: dict):
        """Test registration with duplicate username returns 409."""
        test_user_data["email"] = "different@example.com"
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email returns 422."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "testuser",
            "password": "Password123!",
        })

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password returns 422."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short",
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing fields returns 422."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
        })

        assert response.status_code == 422


class TestAuthLogin:
    """Integration tests for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User, test_user_data: dict):
        """Test successful login returns 200 with access token."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password returns 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword123!",
        })

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client: AsyncClient):
        """Test login with nonexistent email returns 401 (prevents user enumeration)."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Password123!",
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format returns 422."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "Password123!",
        })

        assert response.status_code == 422