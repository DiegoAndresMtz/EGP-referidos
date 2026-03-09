from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.models.models import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token, create_reset_token
)
from app.services.email_service import send_password_reset_email
from app.utils import generate_referral_code
from app.dependencies import get_current_user_optional
from app.config import get_settings

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")
settings = get_settings()
_secure_cookies = settings.BASE_URL.startswith("https")


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

    response = RedirectResponse(url="/dashboard/referidor?welcome=1", status_code=302)
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800, secure=_secure_cookies)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=604800, secure=_secure_cookies)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url=_dashboard_url(user), status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
@limiter.limit("5/minute")
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
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800, secure=_secure_cookies)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=604800, secure=_secure_cookies)
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
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", max_age=1800, secure=_secure_cookies)
    return response


def _dashboard_url(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return "/admin"
    elif user.role == UserRole.ASESOR:
        return "/dashboard/asesor"
    else:
        return "/dashboard/referidor"


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    email = form.get("email", "").strip().lower()

    if not email:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "error": "Por favor ingresa un correo electrónico",
            "form_data": {"email": email},
        })

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        token = create_reset_token(user.email)
        import asyncio
        asyncio.create_task(send_password_reset_email(user.email, token))

    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "success": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."
    })


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    if not token:
        return RedirectResponse(url="/auth/login")

    payload = decode_token(token)
    if not payload or payload.get("type") != "reset":
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "El enlace ha expirado o es inválido."
        })

    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@router.post("/reset-password")
async def reset_password(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    token = form.get("token", "")
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    if not token:
        return RedirectResponse(url="/auth/login")

    payload = decode_token(token)
    if not payload or payload.get("type") != "reset":
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "El enlace ha expirado o es inválido."
        })

    email = payload.get("sub")

    if len(password) < 6:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "La contraseña debe tener al menos 6 caracteres.",
            "token": token
        })

    if password != confirm_password:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "Las contraseñas no coinciden.",
            "token": token
        })

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "Usuario no encontrado."
        })

    user.password_hash = hash_password(password)
    db.add(user)
    await db.commit()

    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "success": "Tu contraseña ha sido actualizada exitosamente."
    })
