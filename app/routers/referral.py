from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, Lead, LeadStatus, UserRole
from app.services.assignment_service import get_next_advisor

router = APIRouter(tags=["referral"])
templates = Jinja2Templates(directory="templates")


@router.get("/r/{code}", response_class=HTMLResponse)
async def referral_landing(
    request: Request,
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Landing page for referral link. Sets referral_code cookie."""
    result = await db.execute(
        select(User).where(User.referral_code == code, User.is_active == True)
    )
    referrer = result.scalar_one_or_none()

    referrer_name = None
    if referrer:
        referrer_name = f"{referrer.name} {referrer.last_name}"

    # Get UTM params
    utm = {
        "utm_source": request.query_params.get("utm_source", ""),
        "utm_medium": request.query_params.get("utm_medium", ""),
        "utm_campaign": request.query_params.get("utm_campaign", ""),
        "utm_content": request.query_params.get("utm_content", ""),
    }

    response = templates.TemplateResponse("referral_landing.html", {
        "request": request,
        "referral_code": code,
        "referrer_name": referrer_name,
        "utm": utm,
    })
    # Set cookie to persist referral code
    response.set_cookie("referral_code", code, max_age=86400 * 30, samesite="lax")
    return response


@router.post("/leads")
async def create_lead(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead from the referral form."""
    form = await request.form()
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip() or None
    city = form.get("city", "").strip() or None
    notes_public = form.get("notes_public", "").strip() or None
    referral_code = form.get("referral_code", "").strip() or request.cookies.get("referral_code", "")
    utm_source = form.get("utm_source", "").strip() or None
    utm_medium = form.get("utm_medium", "").strip() or None
    utm_campaign = form.get("utm_campaign", "").strip() or None
    utm_content = form.get("utm_content", "").strip() or None

    # Validation
    errors = []
    if not first_name or len(first_name) < 2:
        errors.append("Nombre debe tener al menos 2 caracteres")
    if not last_name or len(last_name) < 2:
        errors.append("Apellido debe tener al menos 2 caracteres")
    if not email or "@" not in email:
        errors.append("Email inválido")
    if not notes_public:
        errors.append("Debes indicar qué te interesa")

    if errors:
        return templates.TemplateResponse("referral_landing.html", {
            "request": request,
            "errors": errors,
            "referral_code": referral_code,
            "form_data": {
                "first_name": first_name, "last_name": last_name,
                "email": email, "phone": phone or "", "city": city or "",
                "notes_public": notes_public or "",
            },
        })

    # Find referrer
    referrer_id = None
    if referral_code:
        result = await db.execute(
            select(User).where(User.referral_code == referral_code)
        )
        referrer = result.scalar_one_or_none()
        if referrer:
            referrer_id = referrer.id

    # Assign advisor via round-robin
    advisor_id = await get_next_advisor(db)
    now = datetime.utcnow()

    lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        city=city,
        notes_public=notes_public,
        referrer_id=referrer_id,
        advisor_id=advisor_id,
        assigned_at=now if advisor_id else None,
        status=LeadStatus.NUEVO if advisor_id else LeadStatus.PENDING_ASSIGNMENT,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
    )
    db.add(lead)
    await db.commit()

    return templates.TemplateResponse("lead_success.html", {
        "request": request,
        "lead_name": f"{first_name} {last_name}",
    })
