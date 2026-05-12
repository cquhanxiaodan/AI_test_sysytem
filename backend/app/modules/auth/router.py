from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserProfile
from app.modules.auth.seed_data import SeedUser
from app.modules.auth.service import authenticate, to_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    authenticated = authenticate(payload)
    if authenticated is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token, user = authenticated
    return LoginResponse(access_token=token, user=user)


@router.get("/me", response_model=UserProfile)
def me(current_user: SeedUser = Depends(get_current_user)) -> UserProfile:
    return to_profile(current_user)
