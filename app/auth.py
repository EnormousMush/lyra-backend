"""Local account system: scrypt password hashes, opaque session tokens in an httpOnly cookie."""
import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from . import config
from .config import SESSION_DAYS
from .db import AuthSession, Invite, User, get_session, now

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
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=config.SECURE_COOKIES,
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
    return {"id": u.id, "email": u.email, "name": u.name, "is_admin": bool(u.is_admin),
            "created_at": u.created_at.isoformat()}


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    return user


def _valid_invite(s: Session, code: str | None) -> Invite:
    code = (code or "").strip().upper().replace("-", "")
    inv = s.get(Invite, code) if code else None
    if inv is None:
        raise HTTPException(400, "That invite code is not valid")
    if inv.used_by:
        raise HTTPException(400, "That invite code has already been used")
    if inv.expires_at and inv.expires_at.replace(tzinfo=now().tzinfo) < now():
        raise HTTPException(400, "That invite code has expired")
    return inv


class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    invite: Optional[str] = None

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
    first_user = s.exec(select(User)).first() is None
    invite = None
    if config.INVITE_ONLY and not first_user and body.email != config.ADMIN_EMAIL:
        invite = _valid_invite(s, body.invite)
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password),
                is_admin=first_user or body.email == config.ADMIN_EMAIL)
    s.add(user)
    s.commit()
    s.refresh(user)
    if invite is not None:
        invite.used_by, invite.used_at = user.id, now()
        s.add(invite)
        s.commit()
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


@router.get("/policy")
def policy(s: Session = Depends(get_session)):
    """What the sign-up form needs to know before an account exists."""
    first_user = s.exec(select(User)).first() is None
    return {"invite_only": config.INVITE_ONLY and not first_user,
            "daily_uploads": config.DAILY_UPLOADS, "daily_images": config.DAILY_IMAGES}


class InviteIn(BaseModel):
    note: Optional[str] = None
    days: Optional[int] = 30


def _invite_out(i: Invite, s: Session) -> dict:
    used = s.get(User, i.used_by) if i.used_by else None
    return {"code": i.code, "note": i.note, "created_at": i.created_at.isoformat(),
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
            "used_by": used.email if used else None,
            "used_at": i.used_at.isoformat() if i.used_at else None}


@router.get("/invites")
def list_invites(admin: User = Depends(require_admin), s: Session = Depends(get_session)):
    rows = s.exec(select(Invite).order_by(Invite.created_at.desc())).all()
    return [_invite_out(i, s) for i in rows]


@router.post("/invites")
def create_invite(body: InviteIn, admin: User = Depends(require_admin), s: Session = Depends(get_session)):
    code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    inv = Invite(code=code, created_by=admin.id, note=(body.note or "").strip()[:80] or None,
                 expires_at=now() + timedelta(days=body.days) if body.days else None)
    s.add(inv)
    s.commit()
    return _invite_out(inv, s)


@router.delete("/invites/{code}")
def revoke_invite(code: str, admin: User = Depends(require_admin), s: Session = Depends(get_session)):
    inv = s.get(Invite, code.upper())
    if inv is None:
        raise HTTPException(404, "Invite not found")
    if inv.used_by:
        raise HTTPException(409, "That invite has already been used")
    s.delete(inv)
    s.commit()
    return {"ok": True}
