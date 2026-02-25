import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    REFERIDOR = "REFERIDOR"
    ASESOR = "ASESOR"
    ADMIN = "ADMIN"


class LeadStatus(str, enum.Enum):
    NUEVO = "NUEVO"
    CONTACTADO = "CONTACTADO"
    EN_PROCESO = "EN_PROCESO"
    CERRADO = "CERRADO"
    DESCARTADO = "DESCARTADO"
    PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(UserRole), default=UserRole.REFERIDOR, nullable=False)
    name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    referral_code = Column(String(20), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    referred_leads = relationship(
        "Lead", back_populates="referrer", foreign_keys="Lead.referrer_id"
    )
    assigned_leads = relationship(
        "Lead", back_populates="advisor", foreign_keys="Lead.advisor_id"
    )
    lead_notes = relationship("LeadNote", back_populates="advisor")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    notes_public = Column(Text, nullable=True)
    status = Column(Enum(LeadStatus), default=LeadStatus.NUEVO, nullable=False)

    # Referral
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referrer = relationship(
        "User", back_populates="referred_leads", foreign_keys=[referrer_id]
    )

    # Advisor assignment
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    advisor = relationship(
        "User", back_populates="assigned_leads", foreign_keys=[advisor_id]
    )
    assigned_at = Column(DateTime, nullable=True)

    # UTM tracking
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")


class LeadNote(Base):
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="notes")
    advisor = relationship("User", back_populates="lead_notes")


class AssignmentState(Base):
    __tablename__ = "assignment_state"

    id = Column(Integer, primary_key=True, default=1)
    last_assigned_advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
