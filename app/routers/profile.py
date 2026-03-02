from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User
from app.dependencies import get_current_user
from app.services.auth_service import hash_password, verify_password

router = APIRouter(prefix="/perfil", tags=["perfil"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def perfil_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    ok = request.query_params.get("ok") == "1"
    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "user": current_user,
        "ok": ok,
    })


@router.post("")
async def perfil_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    form = await request.form()
    phone = form.get("phone", "").strip() or None
    current_password = form.get("current_password", "")
    new_password = form.get("new_password", "")

    errors = []

    # Refresh user from DB to ensure it's attached to this session
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    user.phone = phone

    if new_password:
        if not current_password:
            errors.append("Debes ingresar tu contraseña actual para cambiarla")
        elif not verify_password(current_password, user.password_hash):
            errors.append("Contraseña actual incorrecta")
        elif len(new_password) < 6:
            errors.append("La nueva contraseña debe tener al menos 6 caracteres")
        else:
            user.password_hash = hash_password(new_password)

    if errors:
        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "user": user,
            "errors": errors,
        })

    await db.commit()
    return RedirectResponse(url="/perfil?ok=1", status_code=302)
