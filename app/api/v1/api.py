from fastapi import APIRouter
from app.api.v1.endpoints import auth, jobs, profile, community

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(profile.router, prefix="", tags=["profile"])
api_router.include_router(community.router, prefix="/community", tags=["community"])