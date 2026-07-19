from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
