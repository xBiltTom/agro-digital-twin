from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import verify_password, hash_password
from app.models.user import User, UserProfile
from app.schemas.user import ProfileResponse, ProfileUpdate, PasswordChangeRequest
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/profile", tags=["Perfil de Usuario"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.profile:
        # Si aún no existe el perfil, se inicializa
        profile = UserProfile(user_id=current_user.id, preferred_theme="scientific")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile
    return current_user.profile

@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if profile_in.institution is not None:
        profile.institution = profile_in.institution
    if profile_in.department is not None:
        profile.department = profile_in.department
    if profile_in.scientific_specialty is not None:
        profile.scientific_specialty = profile_in.scientific_specialty
    if profile_in.avatar_url is not None:
        profile.avatar_url = profile_in.avatar_url
    if profile_in.bio is not None:
        profile.bio = profile_in.bio
    if profile_in.preferred_theme is not None:
        profile.preferred_theme = profile_in.preferred_theme

    await db.commit()
    await db.refresh(profile)
    return profile

@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    pwd_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(pwd_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta."
        )

    if len(pwd_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres."
        )

    current_user.hashed_password = hash_password(pwd_data.new_password)
    await db.commit()
    return {"message": "Contraseña actualizada exitosamente."}
