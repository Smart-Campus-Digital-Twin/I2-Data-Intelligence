from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth import create_token, require_auth

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


@router.post("/token")
async def login(body: LoginRequest):
    """Get a JWT token. Used by frontend and Socket.IO relay (T6)."""
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    token = create_token(user_id=body.username, username=body.username, role=body.role)
    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   28800,
        "username":     body.username,
        "role":         body.role,
    }


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """Returns info about the currently logged in user."""
    return {
        "user_id":  user.get("sub"),
        "username": user.get("username"),
        "role":     user.get("role"),
    }
