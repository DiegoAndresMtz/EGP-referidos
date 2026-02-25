from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.utils import generate_referral_code
from app.dependencies import get_current_user_optional

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url=_dashboard_url(user), status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    name = form.get("name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip() or None
    password = form.get("password", "")

    # Validation
    errors = []
    if not name or len(name) < 2:
        errors.append("Nombre debe tener al menos 2 caracteres")
    if not last_name or len(last_name) < 2:
        errors.append("Apellido debe tener al menos 2 caracteres")
    if not email or "@" not in email:
        errors.append("Email inválido")
    if not password or len(password) < 6:
        errors.append("Contraseña debe tener al menos 6 caracteres")

    if errors:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "errors": errors,
            "form_data": {"name": name, "last_name": last_name, "email": email, "phone": phone or ""},
        })

    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse("register.html", {
            "request": request,
            "errors": ["Este email ya está registrado"],
            "form_data": {"name": name, "last_name": last_name, "email": email, "phone": phone or ""},
        })

    # Generate unique referral code
    referral_code = generate_referral_code()
    while True:
        result = await db.execute(select(User).where(User.referral_code == referral_code))
        if not result.scalar_one_or_none():
            break
        referral_code = generate_referral_code()

    user = User(
        name=name,
        last_name=last_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=UserRole.REFERIDOR,
        referral_code=referral_code,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Auto-login
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response = RedirectResponse(url="/dashboard/referidor", status_code=302)
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=604800)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url=_dashboard_url(user), status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "errors": ["Credenciales inválidas"],
            "form_data": {"email": email},
        })

    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "errors": ["Tu cuenta está desactivada. Contacta al administrador."],
            "form_data": {"email": email},
        })

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response = RedirectResponse(url=_dashboard_url(user), status_code=302)
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=604800)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


@router.post("/refresh")
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    response = Response(status_code=200)
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800)
    return response


def _dashboard_url(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return "/admin"
    elif user.role == UserRole.ASESOR:
        return "/dashboard/asesor"
    else:
        return "/dashboard/referidor"
