from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False)
    homeowner_name = Column(String(200))
    homeowner_email = Column(String(200))
    homeowner_phone = Column(String(50))
    address = Column(String(500))
    status = Column(String(50), default="intake")  # intake, estimated, reviewed, sent, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    intake = relationship("ProjectIntake", uselist=False, back_populates="project")
    estimate = relationship("Estimate", uselist=False, back_populates="project")
    messages = relationship("Message", back_populates="project", order_by="Message.created_at")


class ProjectIntake(Base):
    __tablename__ = "project_intakes"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    bathroom_sqft = Column(Float)
    shower_sqft = Column(Float)
    has_tub = Column(Boolean, default=False)
    tub_sqft = Column(Float, default=0)

    finish_level = Column(String(20))
    full_gut = Column(Boolean, default=True)
    relocate_plumbing = Column(Boolean, default=False)
    new_shower = Column(Boolean, default=False)
    new_tub = Column(Boolean, default=False)
    new_toilet = Column(Boolean, default=False)
    new_vanity = Column(Boolean, default=False)
    heated_floor = Column(Boolean, default=False)
    new_exhaust_fan = Column(Boolean, default=True)

    description = Column(Text)
    ai_scope_summary = Column(Text)

    project = relationship("Project", back_populates="intake")


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    line_items = Column(JSON, default=list)

    subtotal = Column(Float, default=0)
    gc_markup = Column(Float, default=0)
    sales_tax = Column(Float, default=0)
    total = Column(Float, default=0)

    gc_notes = Column(Text, default="")
    valid_days = Column(Integer, default=30)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="estimate")


# Topic choices for auto-tagging
TOPICS = ["pricing", "plumbing", "electrical", "tile", "timeline",
          "scope", "permits", "warranty", "other"]


class Message(Base):
    """A single homeowner question + answer exchange."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    question = Column(Text, nullable=False)
    answer = Column(Text, default="")

    # "ai" = Claude answered only, "gc" = GC wrote or overrode the answer, "" = unanswered
    answered_by = Column(String(10), default="")

    # Auto-tagged by Claude from TOPICS list
    topic = Column(String(50), default="other")

    # Read tracking
    gc_read = Column(Boolean, default=False)       # GC has seen this question
    homeowner_read = Column(Boolean, default=True) # homeowner always sees their own

    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="messages")
