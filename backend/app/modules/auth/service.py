from secrets import token_urlsafe

from app.modules.auth.schemas import LoginRequest, UserProfile
from app.modules.auth.seed_data import USERS, SeedUser

TOKENS: dict[str, str] = {}


def authenticate(payload: LoginRequest) -> tuple[str, UserProfile] | None:
    user = USERS.get(payload.username)
    if user is None or user.password != payload.password:
        return None

    token = token_urlsafe(32)
    TOKENS[token] = user.id
    return token, to_profile(user)


def get_user_by_token(token: str) -> SeedUser | None:
    user_id = TOKENS.get(token)
    if user_id is None:
        return None
    return next((user for user in USERS.values() if user.id == user_id), None)


def to_profile(user: SeedUser) -> UserProfile:
    return UserProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=list(user.roles),
    )
