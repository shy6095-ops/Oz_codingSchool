import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7


# 운영 MySQL에서는 BIGINT, 테스트 전용 SQLite에서는 자동 증가 가능한 INTEGER를 사용한다.
BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


class UUIDMixin:
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        CHAR(36), primary_key=True, default=uuid7
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC), server_default=text("CURRENT_TIMESTAMP")
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
