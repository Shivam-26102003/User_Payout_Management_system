import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.domain.enums import UserRole, UserStatus

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole
    status: UserStatus

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
