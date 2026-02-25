from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, Lead, LeadNote, LeadStatus, UserRole
from app.dependencies import get_current_user
from app.config import get_settings
from datetime import datetime, timezone

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")
settings = get_settings()


@router.get("/referidor", response_class=HTMLResponse)
async def dashboard_referidor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.REFERIDOR:
        if current_user.role == UserRole.ADMIN:
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/dashboard/asesor", status_code=302)

    # Get lead count
    result = await db.execute(
        select(func.count(Lead.id)).where(Lead.referrer_id == current_user.id)
    )
    total_referidos = result.scalar() or 0

    # Get leads list
    result = await db.execute(
        select(Lead)
        .where(Lead.referrer_id == current_user.id)
        .order_by(Lead.created_at.desc())
    )
    leads = result.scalars().all()

    referral_link = f"{settings.BASE_URL}/r/{current_user.referral_code}"

    return templates.TemplateResponse("dashboard_referidor.html", {
        "request": request,
        "user": current_user,
        "total_referidos": total_referidos,
        "leads": leads,
        "referral_link": referral_link,
        "referral_code": current_user.referral_code,
    })


@router.get("/asesor", response_class=HTMLResponse)
async def dashboard_asesor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ASESOR:
        if current_user.role == UserRole.ADMIN:
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/dashboard/referidor", status_code=302)

    # Get search params
    search = request.query_params.get("search", "").strip()

    query = select(Lead).where(Lead.advisor_id == current_user.id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Lead.first_name.ilike(search_filter)) |
            (Lead.last_name.ilike(search_filter)) |
            (Lead.email.ilike(search_filter)) |
            (Lead.phone.ilike(search_filter))
        )

    query = query.order_by(Lead.created_at.desc())
    result = await db.execute(query)
    leads = result.scalars().all()

    # Get notes for each lead
    lead_notes = {}
    for lead in leads:
        result = await db.execute(
            select(LeadNote)
            .where(LeadNote.lead_id == lead.id)
            .order_by(LeadNote.created_at.desc())
        )
        lead_notes[lead.id] = result.scalars().all()

    # Stats
    total = len(leads)
    nuevos = sum(1 for l in leads if l.status == LeadStatus.NUEVO)
    contactados = sum(1 for l in leads if l.status == LeadStatus.CONTACTADO)
    en_proceso = sum(1 for l in leads if l.status == LeadStatus.EN_PROCESO)
    cerrados = sum(1 for l in leads if l.status == LeadStatus.CERRADO)

    return templates.TemplateResponse("dashboard_asesor.html", {
        "request": request,
        "user": current_user,
        "leads": leads,
        "lead_notes": lead_notes,
        "search": search,
        "stats": {
            "total": total,
            "nuevos": nuevos,
            "contactados": contactados,
            "en_proceso": en_proceso,
            "cerrados": cerrados,
        },
        "statuses": [s.value for s in LeadStatus if s != LeadStatus.PENDING_ASSIGNMENT],
    })


@router.post("/asesor/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ASESOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="No autorizado")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    if current_user.role == UserRole.ASESOR and lead.advisor_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para este lead")

    form = await request.form()
    new_status = form.get("status", "")

    try:
        lead.status = LeadStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido")

    await db.commit()
    return RedirectResponse(url="/dashboard/asesor", status_code=302)


@router.post("/asesor/leads/{lead_id}/notes")
async def add_lead_note(
    lead_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ASESOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="No autorizado")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    if current_user.role == UserRole.ASESOR and lead.advisor_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para este lead")

    form = await request.form()
    note_text = form.get("note", "").strip()

    if not note_text:
        return RedirectResponse(url="/dashboard/asesor", status_code=302)

    note = LeadNote(
        lead_id=lead_id,
        advisor_id=current_user.id,
        note=note_text,
    )
    db.add(note)
    await db.commit()

    return RedirectResponse(url="/dashboard/asesor", status_code=302)
