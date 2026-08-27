"""add user refresh token column and relax xray uploader fk

Revision ID: 0002_refresh_and_xray_fk
Revises: 0001_create_health_schema
Create Date: 2026-08-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_refresh_and_xray_fk"
down_revision: Union[str, Sequence[str], None] = "0001_create_health_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_FK_NAME = "fk_xray_images_uploader_id_users"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("current_refresh_token", sa.String(length=512), nullable=True),
    )

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_fk = next(
        fk["name"]
        for fk in inspector.get_foreign_keys("xray_images")
        if fk["constrained_columns"] == ["uploader_id"]
    )
    op.drop_constraint(existing_fk, "xray_images", type_="foreignkey")
    op.alter_column(
        "xray_images",
        "uploader_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        NEW_FK_NAME,
        "xray_images",
        "users",
        ["uploader_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(NEW_FK_NAME, "xray_images", type_="foreignkey")
    op.alter_column(
        "xray_images",
        "uploader_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(None, "xray_images", "users", ["uploader_id"], ["id"])
    op.drop_column("users", "current_refresh_token")
