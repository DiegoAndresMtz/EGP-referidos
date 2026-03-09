from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, Lead, LeadNote, LeadStatus, UserRole, LeadAdminTask, LossReason, EventoAsistencia
from app.dependencies import get_current_user
from app.config import get_settings
from app.services.email_service import send_payment_date_notification, send_whatsapp_payment_notification
from datetime import datetime, timezone, date
import asyncio
import logging

logger = logging.getLogger(__name__)

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

    # Get notes for each lead
    lead_notes = {}
    for lead in leads:
        result = await db.execute(
            select(LeadNote)
            .where(LeadNote.lead_id == lead.id)
            .order_by(LeadNote.created_at.desc())
        )
        lead_notes[lead.id] = result.scalars().all()

    # Total commission earned (leads cerrados con comisión asignada y NO pagada)
    commission_unpaid_result = await db.execute(
        select(func.sum(Lead.commission_amount))
        .where(Lead.referrer_id == current_user.id)
        .where(Lead.commission_amount != None)
        .where(Lead.commission_paid == False)
    )
    total_commission = commission_unpaid_result.scalar() or 0.0

    # Total commission already paid
    commission_paid_result = await db.execute(
        select(func.sum(Lead.commission_amount))
        .where(Lead.referrer_id == current_user.id)
        .where(Lead.commission_amount != None)
        .where(Lead.commission_paid == True)
    )
    total_paid_commission = commission_paid_result.scalar() or 0.0

    # Rank in leaderboard
    rank_result = await db.execute(
        select(
            User.id,
            func.count(Lead.id).label("cnt"),
        )
        .join(Lead, Lead.referrer_id == User.id)
        .where(User.role == UserRole.REFERIDOR, User.is_active == True, Lead.payment_date.isnot(None))
        .group_by(User.id)
        .order_by(func.count(Lead.id).desc())
    )
    all_rankings = rank_result.all()
    user_rank = None
    for i, row in enumerate(all_rankings, 1):
        if row.id == current_user.id:
            user_rank = i
            break

    # Leads cerrados (para badges)
    closed_count = sum(1 for l in leads if l.status in (LeadStatus.GANADA))

    # SVGs for medals
    svg_star = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'
    svg_flame = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>'
    svg_diamond = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 18 3 22 9 12 21 2 9 6 3"></polygon><polyline points="2 9 22 9"></polyline><polyline points="6 3 12 9 18 3"></polyline><polyline points="12 9 12 21"></polyline></svg>'
    svg_rocket = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path></svg>'
    svg_check = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
    svg_trophy = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path></svg>'

    # Badges/medallas por hitos
    badges = [
        {"icon": svg_star, "name": "Primer Referido", "desc": "Enviaste tu primer referido", "cls": "medal-gold", "unlocked": total_referidos >= 1},
        {"icon": svg_flame, "name": "5 Referidos", "desc": "¡Ya tienes 5 referidos!", "cls": "medal-orange", "unlocked": total_referidos >= 5},
        {"icon": svg_diamond, "name": "10 Referidos", "desc": "¡Increíble! 10 referidos", "cls": "medal-cyan", "unlocked": total_referidos >= 10},
        {"icon": svg_rocket, "name": "25 Referidos", "desc": "¡Eres un referidor élite!", "cls": "medal-purple", "unlocked": total_referidos >= 25, "reward": "Desc. 10% Hotel El Marqués de Manga"},
        {"icon": svg_check, "name": "Primer Cierre", "desc": "Tu primer referido se cerró", "cls": "medal-green", "unlocked": closed_count >= 1, "reward": "Bono de $100.000 COP"},
        {"icon": svg_trophy, "name": "Top Closer", "desc": "3 o más cierres logrados", "cls": "medal-trophy", "unlocked": closed_count >= 3},
    ]

    referral_link = f"{settings.BASE_URL}/r/{current_user.referral_code}"
    show_welcome = request.query_params.get("welcome") == "1"

    # Evento especial: verificar si ya confirmó asistencia
    EVENTO_SLUG = "capacitacion-bocagrande-2026-04-09"
    asistencia_result = await db.execute(
        select(EventoAsistencia).where(
            EventoAsistencia.evento_slug == EVENTO_SLUG,
            EventoAsistencia.user_id == current_user.id,
        )
    )
    evento_confirmado = asistencia_result.scalar_one_or_none() is not None

    return templates.TemplateResponse("dashboard_referidor.html", {
        "request": request,
        "user": current_user,
        "total_referidos": total_referidos,
        "leads": leads,
        "lead_notes": lead_notes,
        "referral_link": referral_link,
        "referral_code": current_user.referral_code,
        "total_commission": total_commission,
        "total_paid_commission": total_paid_commission,
        "user_rank": user_rank,
        "badges": badges,
        "show_welcome": show_welcome,
        "evento_confirmado": evento_confirmado,
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

    query = select(Lead).options(selectinload(Lead.referrer)).where(Lead.advisor_id == current_user.id)

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

    # Get notes and tasks for each lead
    lead_notes = {}
    lead_tasks = {}
    for lead in leads:
        # Notes
        result_notes = await db.execute(
            select(LeadNote)
            .where(LeadNote.lead_id == lead.id)
            .order_by(LeadNote.created_at.desc())
        )
        lead_notes[lead.id] = result_notes.scalars().all()
        
        # Tasks
        result_tasks = await db.execute(
            select(LeadAdminTask)
            .where(LeadAdminTask.lead_id == lead.id)
            .order_by(LeadAdminTask.created_at.desc())
        )
        lead_tasks[lead.id] = result_tasks.scalars().all()

    # Stats
    total = len(leads)
    nuevos = sum(1 for l in leads if l.status == LeadStatus.NUEVO)
    contactados = sum(1 for l in leads if l.status == LeadStatus.CONTACTANDO)
    en_proceso = sum(1 for l in leads if l.status not in (LeadStatus.NUEVO, LeadStatus.CONTACTANDO, LeadStatus.GANADA, LeadStatus.PERDIDA, LeadStatus.PENDING_ASSIGNMENT))
    cerrados = sum(1 for l in leads if l.status in (LeadStatus.GANADA))

    return templates.TemplateResponse("dashboard_asesor.html", {
        "request": request,
        "user": current_user,
        "leads": leads,
        "lead_notes": lead_notes,
        "lead_tasks": lead_tasks,
        "search": search,
        "stats": {
            "total": total,
            "nuevos": nuevos,
            "contactados": contactados,
            "en_proceso": en_proceso,
            "cerrados": cerrados,
        },
        "statuses": [s.value for s in LeadStatus if s != LeadStatus.PENDING_ASSIGNMENT],
        "loss_reasons": [lr.value for lr in LossReason],
        "now": datetime.now(),
        "all_tasks": [t for tasks in lead_tasks.values() for t in tasks],
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
    loss_reason = form.get("loss_reason", "").strip()

    try:
        lead.status = LeadStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido")

    # Save loss reason when status is PERDIDA
    if lead.status == LeadStatus.PERDIDA and loss_reason:
        try:
            LossReason(loss_reason)
        except ValueError:
            raise HTTPException(status_code=400, detail="Razón de pérdida inválida")
        lead.loss_reason = loss_reason
    elif lead.status != LeadStatus.PERDIDA:
        lead.loss_reason = None  # Clear if no longer lost

    await db.commit()
    redirect_url = "/admin" if current_user.role == UserRole.ADMIN else "/dashboard/asesor"
    return RedirectResponse(url=redirect_url, status_code=302)


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


@router.post("/asesor/leads/{lead_id}/payment-date")
async def update_lead_payment_date(
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
    payment_date_str = form.get("payment_date", "").strip()

    if payment_date_str:
        try:
            lead.payment_date = date.fromisoformat(payment_date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")
    else:
        lead.payment_date = None

    await db.commit()

    # Notificar al referidor cuando se confirma fecha de pago
    if lead.payment_date and lead.referrer_id:
        result = await db.execute(select(User).where(User.id == lead.referrer_id))
        referidor = result.scalar_one_or_none()
        if referidor:
            date_display = lead.payment_date.strftime("%d de %B de %Y").lower()
            date_display = date_display[0].upper() + date_display[1:]
            lead_full_name = f"{lead.first_name} {lead.last_name}"

            # Email
            if referidor.email:
                asyncio.create_task(
                    send_payment_date_notification(
                        to_email=referidor.email,
                        referidor_name=referidor.name,
                        lead_name=lead_full_name,
                        payment_date_str=date_display,
                    )
                )

            # WhatsApp
            if referidor.phone:
                asyncio.create_task(
                    send_whatsapp_payment_notification(
                        to_phone=referidor.phone,
                        referidor_name=referidor.name,
                        lead_name=lead_full_name,
                        payment_date_str=date_display,
                    )
                )

    return RedirectResponse(url="/dashboard/asesor", status_code=302)


@router.post("/asesor/leads/{lead_id}/commission")
async def update_lead_commission(
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
    commission_str = form.get("commission", "").strip()

    if commission_str:
        try:
            lead.commission_amount = float(commission_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Monto de comisión inválido")
    else:
        lead.commission_amount = None

    commission_paid = form.get("commission_paid") == "on"
    lead.commission_paid = commission_paid

    await db.commit()

    return RedirectResponse(url="/dashboard/asesor", status_code=302)


@router.post("/asesor/leads/{lead_id}/tasks")
async def add_lead_task(
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
    task_text = form.get("task", "").strip()
    due_date_str = form.get("due_date", "").strip()

    if task_text:
        due_date = None
        if due_date_str:
            from datetime import datetime
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                except ValueError:
                    due_date = None
        new_task = LeadAdminTask(lead_id=lead_id, task=task_text, due_date=due_date)
        db.add(new_task)
        await db.commit()

    return RedirectResponse(url="/dashboard/asesor", status_code=302)


@router.post("/asesor/leads/{lead_id}/tasks/{task_id}/toggle")
async def toggle_lead_task(
    lead_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ASESOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="No autorizado")

    result = await db.execute(
        select(LeadAdminTask).where(LeadAdminTask.id == task_id, LeadAdminTask.lead_id == lead_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # verify advisor owns the lead
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    
    if current_user.role == UserRole.ASESOR:
        if not lead or lead.advisor_id != current_user.id:
             raise HTTPException(status_code=403, detail="No autorizado para este lead")

    task.is_completed = not task.is_completed
    await db.commit()

    return RedirectResponse(url="/dashboard/asesor", status_code=302)


EVENTO_SLUG = "capacitacion-bocagrande-2026-04-09"


@router.post("/referidor/confirmar-evento")
async def confirmar_evento(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.REFERIDOR:
        raise HTTPException(status_code=403, detail="Solo referidores")

    existing = await db.execute(
        select(EventoAsistencia).where(
            EventoAsistencia.evento_slug == EVENTO_SLUG,
            EventoAsistencia.user_id == current_user.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(EventoAsistencia(evento_slug=EVENTO_SLUG, user_id=current_user.id))
        await db.commit()

    return {"ok": True}
