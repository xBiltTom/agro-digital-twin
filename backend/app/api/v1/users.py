from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.models.user import User, Role
from backend.app.schemas.user import UserResponse, UserUpdate
from backend.app.api.deps import require_roles

router = APIRouter(prefix="/users", tags=["Gestión de Usuarios"])

@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO"))
):
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    if role:
        users = [u for u in users if any(r.name == role for r in u.roles)]
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO"))
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles("SUPERADMIN"))
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    if user_in.role_names is not None:
        roles_stmt = select(Role).where(Role.name.in_(user_in.role_names))
        roles_res = await db.execute(roles_stmt)
        user.roles = list(roles_res.scalars().all())

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("SUPERADMIN"))
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible desactivar la propia cuenta de superadministrador."
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    user.is_active = False
    await db.commit()
    return {"message": f"Usuario {user.email} desactivado correctamente."}
