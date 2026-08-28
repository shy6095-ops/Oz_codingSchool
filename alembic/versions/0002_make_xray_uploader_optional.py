"""allow permissionless patient-management image uploads

Revision ID: 0002_make_xray_uploader_optional
Revises: 0001_create_health_schema
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_make_xray_uploader_optional"
down_revision: Union[str, Sequence[str], None] = "0001_create_health_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("xray_images") as batch_op:
        batch_op.alter_column("uploader_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("xray_images") as batch_op:
        batch_op.alter_column("uploader_id", existing_type=sa.Integer(), nullable=False)
