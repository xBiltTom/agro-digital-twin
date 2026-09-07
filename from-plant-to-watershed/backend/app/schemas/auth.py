from typing import Optional, List
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenPayload(BaseModel):
    sub: str
    exp: int

class UserBrief(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    avatar_url: Optional[str] = None
    preferred_theme: Optional[str] = "scientific"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserBrief
