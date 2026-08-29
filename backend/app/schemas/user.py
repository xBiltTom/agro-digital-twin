from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict

# --- PERMISSIONS ---
class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionResponse(PermissionBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- ROLES ---
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleResponse(RoleBase):
    id: str
    permissions: List[PermissionResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RoleBriefResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- PROFILES ---
class ProfileBase(BaseModel):
    institution: Optional[str] = None
    department: Optional[str] = None
    scientific_specialty: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferred_theme: Optional[str] = "scientific"

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- USERS ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role_names: Optional[List[str]] = ["OPERADOR_AGROPECUARIO"]
    institution: Optional[str] = None
    scientific_specialty: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_names: Optional[List[str]] = None

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    roles: List[RoleBriefResponse] = []
    profile: Optional[ProfileResponse] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
