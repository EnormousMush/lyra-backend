"""Local account system: scrypt password hashes, opaque session tokens in an httpOnly cookie."""
import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from .config import SESSION_DAYS
from .db import AuthSession, User, get_session, now

COOKIE = "lyra_session"
router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(s: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    s.add(AuthSession(token_hash=_token_hash(token), user_id=user.id,
                      expires_at=now() + timedelta(days=SESSION_DAYS)))
    s.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax",
                        max_age=SESSION_DAYS * 86400, path="/")


def current_user(lyra_session: str | None = Cookie(default=None),
                 s: Session = Depends(get_session)) -> User:
    if not lyra_session:
        raise HTTPException(401, "Not signed in")
    row = s.get(AuthSession, _token_hash(lyra_session))
    if row is None:
        raise HTTPException(401, "Session expired")
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=now().tzinfo)
    if expires < now():
        s.delete(row)
        s.commit()
        raise HTTPException(401, "Session expired")
    user = s.get(User, row.user_id)
    if user is None:
        raise HTTPException(401, "Account not found")
    return user


def public_user(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "created_at": u.created_at.isoformat()}


class SignupIn(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Enter your name")
        return v[:80]


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    name: str


class PasswordIn(BaseModel):
    current: str
    new: str


@router.post("/signup")
def signup(body: SignupIn, response: Response, s: Session = Depends(get_session)):
    if s.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    s.add(user)
    s.commit()
    s.refresh(user)
    _start_session(s, user, response)
    return public_user(user)


@router.post("/login")
def login(body: LoginIn, response: Response, s: Session = Depends(get_session)):
    user = s.exec(select(User).where(User.email == body.email.strip().lower())).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    _start_session(s, user, response)
    return public_user(user)


@router.post("/logout")
def logout(response: Response, lyra_session: str | None = Cookie(default=None),
           s: Session = Depends(get_session)):
    if lyra_session:
        row = s.get(AuthSession, _token_hash(lyra_session))
        if row:
            s.delete(row)
            s.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


@router.patch("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), s: Session = Depends(get_session)):
    name = body.name.strip()[:80]
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    user.name = name
    s.add(user)
    s.commit()
    return public_user(user)


@router.post("/password")
def change_password(body: PasswordIn, user: User = Depends(current_user), s: Session = Depends(get_session)):
    if not verify_password(body.current, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    user.password_hash = hash_password(body.new)
    s.add(user)
    s.commit()
    return {"ok": True}
