from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User, Lead, UserRole
from app.dependencies import get_current_user_optional

router = APIRouter(tags=["leaderboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Public leaderboard: top referrers ranked by lead count."""
    result = await db.execute(
        select(
            User.id,
            User.name,
            User.last_name,
            func.count(Lead.id).label("total_referidos"),
        )
        .join(Lead, Lead.referrer_id == User.id)
        .where(User.role == UserRole.REFERIDOR, User.is_active == True)
        .group_by(User.id, User.name, User.last_name)
        .order_by(func.count(Lead.id).desc())
        .limit(50)
    )
    rankings = result.all()

    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "rankings": rankings,
        "user": current_user,
    })
