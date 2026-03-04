import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, Enum, Float, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    REFERIDOR = "REFERIDOR"
    ASESOR = "ASESOR"
    ADMIN = "ADMIN"


class LeadStatus(str, enum.Enum):
    NUEVO = "NUEVO"
    CONTACTANDO = "CONTACTANDO"
    CONTACTO_ESTABLECIDO = "CONTACTO_ESTABLECIDO"
    PERFILADO = "PERFILADO"
    LLAMADA_AGENDADA = "LLAMADA_AGENDADA"
    VISITA_AGENDADA = "VISITA_AGENDADA"
    PROPUESTA_REALIZADA = "PROPUESTA_REALIZADA"
    CALIFICADO_FRIO = "CALIFICADO_FRIO"
    GANADA = "GANADA"
    PERDIDA = "PERDIDA"
    PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT"


class LossReason(str, enum.Enum):
    NUNCA_CONTESTO = "Nunca contestó"
    DATOS_INCORRECTOS = "Datos incorrectos"
    YA_COMPRO = "Ya compró"
    NO_ES_EL_MOMENTO = "No es el momento"
    SPAM = "Spam"
    DEJO_DE_RESPONDER = "Dejó de responder"
    PRECIO = "Precio"
    TIEMPO_DE_ENTREGA = "Tiempo de entrega"
    UBICACION = "Ubicación"
    AMENIDADES = "Amenidades"
    NO_LE_INTERESA = "No le interesa"
    COMPRO_EN_OTRO_PROYECTO = "Compró en otro proyecto"
    PLAN_PAGO_NO_ACEPTADO = "Plan de pago propuesto no aceptado"
    MAL_PERFILADO = "Mal perfilado"


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
    loss_reason = Column(String(255), nullable=True)

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

    payment_date = Column(Date, nullable=True)
    commission_amount = Column(Float, nullable=True)
    commission_paid = Column(Boolean, default=False, nullable=False, server_default="0")

    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    admin_tasks = relationship("LeadAdminTask", back_populates="lead", cascade="all, delete-orphan")


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


class LeadAdminTask(Base):
    __tablename__ = "lead_admin_tasks"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    task = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False, server_default="0")
    created_at = Column(DateTime, default=func.now(), nullable=False)
    due_date = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="admin_tasks")
