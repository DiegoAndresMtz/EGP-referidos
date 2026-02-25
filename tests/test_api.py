import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, Lead, UserRole, LeadStatus, AssignmentState
from app.services.auth_service import hash_password
from app.services.assignment_service import get_next_advisor


@pytest.mark.asyncio
async def test_home_page(client: AsyncClient):
    """Test home page loads."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "EGP Referidos" in response.text


@pytest.mark.asyncio
async def test_register_page(client: AsyncClient):
    """Test register page loads."""
    response = await client.get("/auth/register")
    assert response.status_code == 200
    assert "Crear Cuenta" in response.text


@pytest.mark.asyncio
async def test_login_page(client: AsyncClient):
    """Test login page loads."""
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar Sesión" in response.text


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration flow."""
    response = await client.post(
        "/auth/register",
        data={
            "name": "Test",
            "last_name": "User",
            "email": "test@test.com",
            "phone": "+57 300 123 4567",
            "password": "Test123!",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/dashboard/referidor" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    """Test that duplicate emails are rejected."""
    user = User(
        name="Existing",
        last_name="User",
        email="dup@test.com",
        password_hash=hash_password("Test123!"),
        role=UserRole.REFERIDOR,
        referral_code="abc12345",
    )
    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/auth/register",
        data={
            "name": "New",
            "last_name": "User",
            "email": "dup@test.com",
            "password": "Test123!",
        },
    )
    assert response.status_code == 200
    assert "ya está registrado" in response.text


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient, db_session: AsyncSession):
    """Test login with valid credentials."""
    user = User(
        name="Login",
        last_name="Test",
        email="login@test.com",
        password_hash=hash_password("Test123!"),
        role=UserRole.REFERIDOR,
        referral_code="login123",
    )
    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/auth/login",
        data={
            "email": "login@test.com",
            "password": "Test123!",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/auth/login",
        data={
            "email": "nobody@test.com",
            "password": "wrong",
        },
    )
    assert response.status_code == 200
    assert "inválidas" in response.text


@pytest.mark.asyncio
async def test_leaderboard_page(client: AsyncClient):
    """Test leaderboard page loads."""
    response = await client.get("/leaderboard")
    assert response.status_code == 200
    assert "Ranking" in response.text


@pytest.mark.asyncio
async def test_referral_landing(client: AsyncClient, db_session: AsyncSession):
    """Test referral landing loads with valid code."""
    user = User(
        name="Referrer",
        last_name="Test",
        email="ref@test.com",
        password_hash=hash_password("Test123!"),
        role=UserRole.REFERIDOR,
        referral_code="REF12345",
    )
    db_session.add(user)
    await db_session.commit()

    response = await client.get("/r/REF12345")
    assert response.status_code == 200
    assert "Referrer" in response.text


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient, db_session: AsyncSession):
    """Test lead creation."""
    referrer = User(
        name="Referrer",
        last_name="Lead",
        email="reflead@test.com",
        password_hash=hash_password("Test123!"),
        role=UserRole.REFERIDOR,
        referral_code="LEADTEST",
    )
    db_session.add(referrer)
    await db_session.commit()

    response = await client.post(
        "/leads",
        data={
            "first_name": "New",
            "last_name": "Lead",
            "email": "newlead@test.com",
            "phone": "123456",
            "city": "Bogotá",
            "referral_code": "LEADTEST",
        },
    )
    assert response.status_code == 200
    assert "Gracias" in response.text


@pytest.mark.asyncio
async def test_round_robin_assignment(db_session: AsyncSession):
    """Test round-robin advisor assignment."""
    # Create advisors
    for i in range(3):
        advisor = User(
            name=f"Advisor{i}",
            last_name="Test",
            email=f"advisor{i}@test.com",
            password_hash=hash_password("Test123!"),
            role=UserRole.ASESOR,
            is_active=True,
        )
        db_session.add(advisor)
    await db_session.commit()

    # Get advisor IDs
    result = await db_session.execute(
        select(User).where(User.role == UserRole.ASESOR).order_by(User.id)
    )
    advisors = result.scalars().all()
    advisor_ids = [a.id for a in advisors]

    # Test round-robin
    assigned = []
    for _ in range(6):
        aid = await get_next_advisor(db_session)
        assigned.append(aid)

    # Should cycle through: a0, a1, a2, a0, a1, a2
    assert assigned[0] == advisor_ids[0]
    assert assigned[1] == advisor_ids[1]
    assert assigned[2] == advisor_ids[2]
    assert assigned[3] == advisor_ids[0]
    assert assigned[4] == advisor_ids[1]
    assert assigned[5] == advisor_ids[2]


@pytest.mark.asyncio
async def test_no_advisors_returns_none(db_session: AsyncSession):
    """Test that no active advisors returns None."""
    aid = await get_next_advisor(db_session)
    assert aid is None
