from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import Role, Permission, User
from app.schemas.user import RoleResponse, PermissionResponse
from app.api.deps import require_roles

router = APIRouter(prefix="/roles", tags=["Roles y Permisos"])

@router.get("", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"))
):
    stmt = select(Role)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    return roles

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles("SUPERADMIN"))
):
    stmt = select(Permission)
    result = await db.execute(stmt)
    perms = result.scalars().all()
    return perms
