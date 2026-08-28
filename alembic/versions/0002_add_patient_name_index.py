"""add patient name index"""

from alembic import op


revision = "0002_add_patient_name_index"
down_revision = "0001_create_health_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_patients_name", "patients", ["name"])


def downgrade() -> None:
    op.drop_index("ix_patients_name", table_name="patients")
