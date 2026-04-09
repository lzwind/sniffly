"""SQLAlchemy models for Sniffly Site."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    __allow_unmapped__ = True


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    username: str = Column(String(50), unique=True, nullable=False)
    password_hash: str = Column(String(255), nullable=False)
    is_admin: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    shares: list["Share"] = relationship("Share", back_populates="user", cascade="all, delete-orphan")


class Share(Base):
    __tablename__ = "shares"
    __table_args__ = (UniqueConstraint("user_id", "project_name", name="uix_user_project"),)

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    uuid: str = Column(String(36), unique=True, nullable=False)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_name: str = Column(String(255), nullable=False)
    stats: dict = Column(JSON, nullable=False, default=dict)
    messages: list = Column(JSON, nullable=False, default=list)
    is_public: bool = Column(Boolean, default=False, nullable=False)
    is_featured: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: "User" = relationship("User", back_populates="shares")
