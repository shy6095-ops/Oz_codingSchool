from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import BIGINT_ID, TimestampMixin
from app.models.user import Gender


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Gender] = mapped_column(nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient"
    )
