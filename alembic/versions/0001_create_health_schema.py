"""create health schema

Revision ID: 0001_create_health_schema
Revises:
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_health_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


gender_enum = sa.Enum("M", "F", name="gender")
role_enum = sa.Enum("PENDING", "STAFF", "ADMIN", name="role")
department_enum = sa.Enum("MEDICAL", "DEV", "RESEARCH", name="department")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("phone_number", sa.String(length=20), unique=True, nullable=False),
        sa.Column("gender", gender_enum, nullable=False),
        sa.Column("department", department_enum, nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("current_timestamp(0)"),
        ),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("age", sa.SmallInteger(), nullable=False),
        sa.Column("gender", gender_enum, nullable=False),
        sa.Column("phone", sa.String(length=11), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("current_timestamp(0)"),
        ),
    )
    op.create_table(
        "medical_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("chart_number", sa.String(length=50), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
    )
    op.create_table(
        "ai_analysis_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("is_pneumonia", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column("heatmap_url", sa.String(length=255), nullable=False),
        sa.Column("ai_model", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.ForeignKeyConstraint(["record_id"], ["medical_records.id"]),
    )
    op.create_table(
        "xray_images",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("shooting_datetime", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("current_timestamp(0)"),
        ),
        sa.ForeignKeyConstraint(["record_id"], ["medical_records.id"]),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("xray_images")
    op.drop_table("ai_analysis_results")
    op.drop_table("medical_records")
    op.drop_table("patients")
    op.drop_table("users")
