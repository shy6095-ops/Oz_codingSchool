from decimal import Decimal

from sqlalchemy import Boolean, DECIMAL, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class AiAnalysisResult(TimestampMixin, Base):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medical_records.id"), nullable=False
    )
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    heatmap_url: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)

    medical_record: Mapped["MedicalRecord"] = relationship(
        back_populates="ai_analysis_results"
    )
