from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, UserRole, AssignmentState


async def get_next_advisor(db: AsyncSession) -> Optional[int]:
    """
    Round-robin assignment: pick next active advisor.
    Ensures only truly active advisors are selected by forcing a fresh query.
    """
    # Get or create assignment state
    result = await db.execute(select(AssignmentState).where(AssignmentState.id == 1))
    state = result.scalar_one_or_none()

    if state is None:
        state = AssignmentState(id=1, last_assigned_advisor_id=None)
        db.add(state)
        await db.flush()

    # Force fresh read: get ONLY active advisors ordered by id
    result = await db.execute(
        select(User)
        .where(
            User.role == UserRole.ASESOR,
            User.is_active.is_(True),
        )
        .order_by(User.id)
        .execution_options(populate_existing=True)
    )
    advisors = result.scalars().all()

    if not advisors:
        # Reset state since there are no active advisors
        state.last_assigned_advisor_id = None
        state.updated_at = datetime.utcnow()
        await db.flush()
        return None

    # Find the next advisor after last_assigned
    last_id = state.last_assigned_advisor_id
    next_advisor = None

    if last_id is None:
        next_advisor = advisors[0]
    else:
        # Find position of last assigned advisor in active list
        found = False
        for i, advisor in enumerate(advisors):
            if advisor.id == last_id:
                # Pick the next one (wrap around)
                next_advisor = advisors[(i + 1) % len(advisors)]
                found = True
                break
        if not found:
            # Last assigned advisor no longer active, start from first active
            next_advisor = advisors[0]

    # Double-check: verify the selected advisor is truly active
    verify_result = await db.execute(
        select(User).where(
            User.id == next_advisor.id,
            User.role == UserRole.ASESOR,
            User.is_active.is_(True),
        )
    )
    verified = verify_result.scalar_one_or_none()

    if not verified:
        # Selected advisor became inactive, pick the first active one
        next_advisor = advisors[0]

    # Update state
    state.last_assigned_advisor_id = next_advisor.id
    state.updated_at = datetime.utcnow()
    await db.flush()

    return next_advisor.id


async def assign_pending_leads(db: AsyncSession) -> int:
    """Assign all pending leads to active advisors. Returns count assigned."""
    from app.models.models import Lead, LeadStatus

    result = await db.execute(
        select(Lead).where(Lead.status == LeadStatus.PENDING_ASSIGNMENT)
    )
    pending_leads = result.scalars().all()

    assigned_count = 0
    for lead in pending_leads:
        advisor_id = await get_next_advisor(db)
        if advisor_id is None:
            break
        lead.advisor_id = advisor_id
        lead.assigned_at = datetime.utcnow()
        lead.status = LeadStatus.NUEVO
        assigned_count += 1

    await db.commit()
    return assigned_count
