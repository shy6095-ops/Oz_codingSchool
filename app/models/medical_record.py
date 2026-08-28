from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class MedicalRecord(TimestampMixin, Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), nullable=False
    )
    chart_number: Mapped[str] = mapped_column(String(50), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan"
    )
    ai_analysis_results: Mapped[list["AiAnalysisResult"]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan"
    )
