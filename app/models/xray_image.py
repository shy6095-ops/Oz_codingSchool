from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class XrayImage(TimestampMixin, Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medical_records.id"), nullable=False
    )
    # 환자 관리 API는 인증을 요구하지 않는 최소 과제 범위이므로 업로더 정보는 선택값이다.
    uploader_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="xray_images")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_xray_images")
