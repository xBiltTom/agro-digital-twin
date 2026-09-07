from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token
from app.models.user import User, Role, UserProfile
from app.schemas.auth import LoginRequest, TokenResponse, UserBrief
from app.schemas.user import UserCreate, UserResponse
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == login_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas (correo o contraseña)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario se encuentra desactivada."
        )

    access_token = create_access_token(subject=user.id)
    role_names = [role.name for role in user.roles]

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserBrief(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            roles=role_names,
            avatar_url=user.profile.avatar_url if user.profile else None,
            preferred_theme=user.profile.preferred_theme if user.profile else "scientific"
        )
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Verificar si el correo ya existe
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya se encuentra registrado."
        )

    # Hashear contraseña
    hashed_pwd = hash_password(user_in.password)

    # Public registration is deliberately restricted to the least-privileged role.
    target_roles = ["OPERADOR_AGROPECUARIO"]
    roles_stmt = select(Role).where(Role.name.in_(target_roles))
    roles_res = await db.execute(roles_stmt)
    assigned_roles = list(roles_res.scalars().all())
    if len(assigned_roles) != len(target_roles):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El catálogo RBAC no está inicializado; no se puede completar el registro."
        )

    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        is_active=True,
        is_verified=False,
        roles=assigned_roles
    )
    db.add(new_user)
    await db.flush()

    # Crear perfil asociado
    new_profile = UserProfile(
        user_id=new_user.id,
        institution=user_in.institution,
        scientific_specialty=user_in.scientific_specialty,
        preferred_theme="scientific"
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_user)

    return new_user

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    return current_user

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    new_token = create_access_token(subject=current_user.id)
    role_names = [role.name for role in current_user.roles]

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserBrief(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            roles=role_names,
            avatar_url=current_user.profile.avatar_url if current_user.profile else None,
            preferred_theme=current_user.profile.preferred_theme if current_user.profile else "scientific"
        )
    )
