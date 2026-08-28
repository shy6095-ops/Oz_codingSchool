from enum import Enum

from sqlalchemy import Boolean, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class Gender(str, Enum):
    M = "M"
    F = "F"


class Role(str, Enum):
    PENDING = "PENDING"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class Department(str, Enum):
    MEDICAL = "MEDICAL"
    DEV = "DEV"
    RESEARCH = "RESEARCH"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(20))
    phone_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    gender: Mapped[Gender] = mapped_column(SqlEnum(Gender, name="gender"), nullable=False)
    department: Mapped[Department] = mapped_column(
        SqlEnum(Department, name="department"), nullable=False
    )
    role: Mapped[Role] = mapped_column(SqlEnum(Role, name="role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    uploaded_xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="uploader",
        cascade="all, delete-orphan",
    )
