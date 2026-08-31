"""Prevent duplicate predictions from the same model for one medical record.

Revision ID: 0003_add_analysis_model_unique_constraint
Revises: 0002_add_patient_name_index
"""

from alembic import op


revision = "0003_add_analysis_model_unique_constraint"
down_revision = "0002_add_patient_name_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_analysis_record_model",
        "ai_analysis_results",
        ["record_id", "ai_model"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analysis_record_model", "ai_analysis_results", type_="unique"
    )
