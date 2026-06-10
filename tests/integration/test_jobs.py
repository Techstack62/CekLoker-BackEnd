"""Integration tests for jobs/drafts/history endpoints."""
import io
import pytest
from httpx import AsyncClient
from app.models.loker_check import LokerCheck
from app.models.user import User


class TestDraftWorkflow:
    """Integration tests for draft workflow."""

    @pytest.mark.asyncio
    async def test_get_drafts(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test getting user's drafts returns 200."""
        check = LokerCheck(
            user_id=test_user.id, job_title="Test Job", is_draft=True
        )
        db_session.add(check)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/jobs/drafts")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_drafts_pagination(self, authenticated_client: AsyncClient):
        """Test drafts pagination works correctly."""
        response = await authenticated_client.get("/api/v1/jobs/drafts?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

    @pytest.mark.asyncio
    async def test_get_drafts_invalid_pagination(
        self, authenticated_client: AsyncClient
    ):
        """Test drafts with invalid pagination returns 422."""
        response = await authenticated_client.get("/api/v1/jobs/drafts?page=0")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_draft_detail(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test getting draft detail returns 200."""
        check = LokerCheck(
            user_id=test_user.id, job_title="Test Job", is_draft=True
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.get(f"/api/v1/jobs/drafts/{check.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_title"] == "Test Job"
        assert data["is_draft"] is True

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self, authenticated_client: AsyncClient):
        """Test getting nonexistent draft returns 404."""
        response = await authenticated_client.get("/api/v1/jobs/drafts/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_draft_other_user(
        self,
        authenticated_client: AsyncClient,
        db_session,
        other_user: User,
    ):
        """Test getting another user's draft returns 403."""
        check = LokerCheck(
            user_id=other_user.id, job_title="Other's Draft", is_draft=True
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.get(f"/api/v1/jobs/drafts/{check.id}")
        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_delete_draft(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test deleting draft returns 200."""
        check = LokerCheck(
            user_id=test_user.id, job_title="Job to Delete", is_draft=True
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)
        check_id = check.id

        response = await authenticated_client.delete(f"/api/v1/jobs/drafts/{check_id}")
        assert response.status_code == 200

        response = await authenticated_client.get(f"/api/v1/jobs/drafts/{check_id}")
        assert response.status_code == 404


class TestHistoryWorkflow:
    """Integration tests for history endpoints."""

    @pytest.mark.asyncio
    async def test_get_history(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test getting history returns 200."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Submitted Job",
            is_draft=False,
            scam_percentage=25.0,
            scam_category="Mencurigakan",
        )
        db_session.add(check)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/jobs/history")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_history_detail(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test getting history detail returns 200."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Test Job",
            is_draft=False,
            scam_percentage=10.0,
            scam_category="Aman",
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.get(f"/api/v1/jobs/history/{check.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_title"] == "Test Job"
        assert data["scam_percentage"] == 10.0

    @pytest.mark.asyncio
    async def test_get_history_not_found(self, authenticated_client: AsyncClient):
        """Test getting nonexistent history returns 404."""
        response = await authenticated_client.get("/api/v1/jobs/history/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_history_other_user(
        self,
        authenticated_client: AsyncClient,
        db_session,
        other_user: User,
    ):
        """Test getting another user's history returns 403."""
        check = LokerCheck(
            user_id=other_user.id,
            job_title="Other's History",
            is_draft=False,
            scam_percentage=50.0,
            scam_category="Scam",
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.get(f"/api/v1/jobs/history/{check.id}")
        assert response.status_code == 403


class TestSharingWorkflow:
    """Integration tests for community sharing endpoints."""

    @pytest.mark.asyncio
    async def test_share_to_community(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test sharing to community returns 200."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Job to Share",
            is_draft=False,
            scam_percentage=75.0,
            scam_category="Scam",
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.post(
            f"/api/v1/jobs/history/{check.id}/share",
            json={"anonymous": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_shared"] is True

    @pytest.mark.asyncio
    async def test_share_draft_not_allowed(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test sharing a draft returns 400."""
        check = LokerCheck(
            user_id=test_user.id, job_title="Draft Job", is_draft=True
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.post(
            f"/api/v1/jobs/history/{check.id}/share"
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unshare_from_community(
        self, authenticated_client: AsyncClient, db_session, test_user: User
    ):
        """Test unsharing from community returns 200."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Job to Unshare",
            is_draft=False,
            is_shared=True,
            scam_percentage=80.0,
            scam_category="Scam",
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)

        response = await authenticated_client.delete(
            f"/api/v1/jobs/history/{check.id}/share"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_shared"] is False


class TestAuthorizationRequired:
    """Tests for unauthorized access to protected endpoints."""

    @pytest.mark.asyncio
    async def test_get_drafts_unauthorized(self, client: AsyncClient):
        """Test getting drafts without auth returns 401."""
        response = await client.get("/api/v1/jobs/drafts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_history_unauthorized(self, client: AsyncClient):
        """Test getting history without auth returns 401."""
        response = await client.get("/api/v1/jobs/history")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_draft_unauthorized(self, client: AsyncClient):
        """Test submitting draft without auth returns 401."""
        response = await client.post("/api/v1/jobs/drafts/1/submit")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_share_unauthorized(self, client: AsyncClient):
        """Test sharing without auth returns 401."""
        response = await client.post("/api/v1/jobs/history/1/share")
        assert response.status_code == 401