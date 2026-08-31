"""make heatmap url optional

Revision ID: 0002_make_heatmap_url_optional
Revises: 0001_create_health_schema
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_make_heatmap_url_optional"
down_revision: Union[str, Sequence[str], None] = "0001_create_health_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_analysis_results",
        "heatmap_url",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "ai_analysis_results",
        "heatmap_url",
        existing_type=sa.String(length=255),
        nullable=False,
    )
