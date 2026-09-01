"""make heatmap url optional

Revision ID: 0002_make_heatmap_url_optional
Revises: 0002_nullable_heatmap
Create Date: 2026-08-31
"""

from typing import Sequence, Union


revision: str = "0002_make_heatmap_url_optional"
down_revision: Union[str, Sequence[str], None] = "0002_nullable_heatmap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
