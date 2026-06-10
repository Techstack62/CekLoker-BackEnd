from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    full_name: Optional[str] = None


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# Properties to receive via API on update
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)


# Properties to return via API
class UserResponse(UserBase):
    id: int
    profile_image: Optional[str] = None

    model_config = {"from_attributes": True}


# Profile response with additional info
class ProfileResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
