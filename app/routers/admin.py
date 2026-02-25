from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, Lead, LeadNote, LeadStatus, UserRole
from app.dependencies import get_current_user
from app.services.auth_service import hash_password
from app.services.assignment_service import assign_pending_leads, get_next_advisor
from app.utils import generate_referral_code

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    tab = request.query_params.get("tab", "overview")

    # Stats
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_referidores = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.REFERIDOR)
    )).scalar() or 0
    total_asesores = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.ASESOR)
    )).scalar() or 0
    total_leads = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
    pending_leads = (await db.execute(
        select(func.count(Lead.id)).where(Lead.status == LeadStatus.PENDING_ASSIGNMENT)
    )).scalar() or 0

    # Users list
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    # Advisors list
    result = await db.execute(
        select(User).where(User.role == UserRole.ASESOR).order_by(User.created_at.desc())
    )
    advisors = result.scalars().all()

    # Advisor lead counts
    advisor_lead_counts = {}
    for advisor in advisors:
        count = (await db.execute(
            select(func.count(Lead.id)).where(Lead.advisor_id == advisor.id)
        )).scalar() or 0
        advisor_lead_counts[advisor.id] = count

    # Leads list
    result = await db.execute(
        select(Lead).order_by(Lead.created_at.desc())
    )
    leads = result.scalars().all()

    # For leads, get referrer and advisor names
    lead_details = []
    for lead in leads:
        referrer_name = ""
        advisor_name = ""
        if lead.referrer_id:
            r = (await db.execute(select(User).where(User.id == lead.referrer_id))).scalar_one_or_none()
            if r:
                referrer_name = f"{r.name} {r.last_name}"
        if lead.advisor_id:
            a = (await db.execute(select(User).where(User.id == lead.advisor_id))).scalar_one_or_none()
            if a:
                advisor_name = f"{a.name} {a.last_name}"
        lead_details.append({
            "lead": lead,
            "referrer_name": referrer_name,
            "advisor_name": advisor_name,
        })

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": current_user,
        "tab": tab,
        "stats": {
            "total_users": total_users,
            "total_referidores": total_referidores,
            "total_asesores": total_asesores,
            "total_leads": total_leads,
            "pending_leads": pending_leads,
        },
        "users": users,
        "advisors": advisors,
        "advisor_lead_counts": advisor_lead_counts,
        "lead_details": lead_details,
        "all_advisors": [a for a in advisors if a.is_active],
    })


@router.post("/advisors")
async def create_advisor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    form = await request.form()
    name = form.get("name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip() or None
    password = form.get("password", "").strip()

    if not all([name, last_name, email, password]):
        return RedirectResponse(url="/admin?tab=advisors&error=campos_requeridos", status_code=302)

    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return RedirectResponse(url="/admin?tab=advisors&error=email_existe", status_code=302)

    advisor = User(
        name=name,
        last_name=last_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=UserRole.ASESOR,
        is_active=True,
    )
    db.add(advisor)
    await db.commit()

    return RedirectResponse(url="/admin?tab=advisors", status_code=302)


@router.post("/advisors/{advisor_id}/toggle")
async def toggle_advisor(
    advisor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    result = await db.execute(
        select(User).where(User.id == advisor_id, User.role == UserRole.ASESOR)
    )
    advisor = result.scalar_one_or_none()

    if not advisor:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")

    advisor.is_active = not advisor.is_active
    await db.commit()

    return RedirectResponse(url="/admin?tab=advisors", status_code=302)


@router.post("/leads/{lead_id}/reassign")
async def reassign_lead(
    lead_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    form = await request.form()
    new_advisor_id = form.get("advisor_id")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    if new_advisor_id:
        new_advisor_id = int(new_advisor_id)
        result = await db.execute(
            select(User).where(User.id == new_advisor_id, User.role == UserRole.ASESOR)
        )
        advisor = result.scalar_one_or_none()
        if not advisor:
            raise HTTPException(status_code=404, detail="Asesor no encontrado")

        lead.advisor_id = new_advisor_id
        lead.assigned_at = datetime.now(timezone.utc)
        if lead.status == LeadStatus.PENDING_ASSIGNMENT:
            lead.status = LeadStatus.NUEVO

    await db.commit()
    return RedirectResponse(url="/admin?tab=leads", status_code=302)


@router.post("/assign-pending")
async def assign_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    count = await assign_pending_leads(db)
    return RedirectResponse(url=f"/admin?tab=leads&assigned={count}", status_code=302)
