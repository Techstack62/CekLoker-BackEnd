from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    profile_image = Column(String, nullable=True)  # Path ke gambar profile
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    loker_checks = relationship("LokerCheck", back_populates="user", cascade="all, delete-orphan")
