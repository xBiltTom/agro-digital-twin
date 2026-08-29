from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de autenticación",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo en el sistema"
        )
    return current_user

def require_roles(*allowed_roles: str) -> Callable:
    """Verifica que el usuario actual tenga al menos uno de los roles permitidos."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_role_names = [role.name for role in current_user.roles]
        
        # SUPERADMIN siempre tiene acceso irrestricto
        if "SUPERADMIN" in user_role_names:
            return current_user
            
        has_permission = any(role in allowed_roles for role in user_role_names)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def require_permissions(*required_permissions: str) -> Callable:
    """Verifica que el usuario posea los permisos específicos requeridos."""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_role_names = [role.name for role in current_user.roles]
        if "SUPERADMIN" in user_role_names:
            return current_user
            
        all_user_perms = set()
        for role in current_user.roles:
            for perm in role.permissions:
                all_user_perms.add(perm.name)
                
        missing = [p for p in required_permissions if p not in all_user_perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Requiere: {', '.join(missing)}"
            )
        return current_user
    return permission_checker
