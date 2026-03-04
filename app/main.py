import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.models.models import User, UserRole, AssignmentState
from app.services.auth_service import hash_password
from app.dependencies import get_current_user_optional
from sqlalchemy import select, text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


async def init_db():
    """Create tables and seed admin user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Apply any missing columns (safe to run on every startup)
        if settings.DATABASE_URL.startswith("postgresql"):
            await conn.execute(text(
                "ALTER TABLE leads ADD COLUMN IF NOT EXISTS payment_date DATE"
            ))
            await conn.execute(text(
                "ALTER TABLE leads ADD COLUMN IF NOT EXISTS commission_amount FLOAT"
            ))
            await conn.execute(text(
                "ALTER TABLE leads ADD COLUMN IF NOT EXISTS commission_paid BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(text(
                "ALTER TABLE leads ADD COLUMN IF NOT EXISTS loss_reason VARCHAR(255)"
            ))

    # Add new enum values outside of transaction (PostgreSQL requires this for ALTER TYPE ADD VALUE)
    if settings.DATABASE_URL.startswith("postgresql"):
        async with engine.connect() as conn:
            await conn.execute(text("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'CONTACTANDO'"))
            await conn.execute(text("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'PROPUESTA_REALIZADA'"))
            await conn.execute(text("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'GANADA'"))
            await conn.execute(text("ALTER TYPE leadstatus ADD VALUE IF NOT EXISTS 'PERDIDA'"))
            await conn.commit()

    async with engine.begin() as conn:
        if settings.DATABASE_URL.startswith("postgresql"):
            # Migrate old statuses to new ones (safe: only updates rows with old values)
            await conn.execute(text("UPDATE leads SET status = 'CONTACTANDO'::leadstatus WHERE status::text = 'CONTACTADO'"))
            await conn.execute(text("UPDATE leads SET status = 'PROPUESTA_REALIZADA'::leadstatus WHERE status::text = 'EN_PROCESO'"))
            await conn.execute(text("UPDATE leads SET status = 'GANADA'::leadstatus WHERE status::text = 'CERRADO'"))
            await conn.execute(text("UPDATE leads SET status = 'PERDIDA'::leadstatus WHERE status::text = 'DESCARTADO'"))
        else:
            # SQLite: ALTER TABLE no soporta IF NOT EXISTS, usamos try/except
            for stmt in [
                "ALTER TABLE leads ADD COLUMN payment_date DATE",
                "ALTER TABLE leads ADD COLUMN commission_amount FLOAT",
                "ALTER TABLE leads ADD COLUMN commission_paid BOOLEAN NOT NULL DEFAULT 0",
                "ALTER TABLE leads ADD COLUMN loss_reason VARCHAR(255)",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass  # La columna ya existe
            # Migrate old statuses to new ones
            for old, new in [("CONTACTADO", "CONTACTANDO"), ("EN_PROCESO", "PROPUESTA_REALIZADA"), ("CERRADO", "GANADA"), ("DESCARTADO", "PERDIDA")]:
                try:
                    await conn.execute(text(f"UPDATE leads SET status = '{new}' WHERE status = '{old}'"))
                except Exception:
                    pass

    # Seed admin user
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                name=settings.ADMIN_NAME,
                last_name=settings.ADMIN_LAST_NAME,
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")

        # Create assignment state if not exists
        result = await db.execute(select(AssignmentState).where(AssignmentState.id == 1))
        if not result.scalar_one_or_none():
            state = AssignmentState(id=1)
            db.add(state)
            await db.commit()
            logger.info("Assignment state initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Application started")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
from app.routers import auth, referral, dashboard, leaderboard, admin, profile

app.include_router(auth.router)
app.include_router(referral.router)
app.include_router(dashboard.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)
app.include_router(profile.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = None
    try:
        from app.database import get_db
        async with AsyncSessionLocal() as db:
            user = await get_current_user_optional(request, db)
    except Exception:
        pass
    return templates.TemplateResponse("home.html", {"request": request, "user": user})
