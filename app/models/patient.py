from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.models.user import Gender

if TYPE_CHECKING:
    from app.models.medical_record import MedicalRecord


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Gender] = mapped_column(nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_patients_name", "name"),)
