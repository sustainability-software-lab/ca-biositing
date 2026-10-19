"""Add qc_review_decision table

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: Union[str, Sequence[str], None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "qc_review_decision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("etl_run_id", sa.Integer(), nullable=True),
        sa.Column("lineage_group_id", sa.Integer(), nullable=True),
        sa.Column("record_table", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("record_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("replicate_group_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("resource_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("analysis_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("parameter_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "flag_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=sa.text("'analyst_flagged'"),
        ),
        sa.Column("flag_trigger_value", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("old_qc_pass", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("new_qc_pass", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "decision_status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("decision_action", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("rationale_chips", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "review_note",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("submitted_by_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("assigned_to_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("resolved_by_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "synced_to_gsheet",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("gsheet_synced_at", sa.DateTime(), nullable=True),
        sa.Column("gsheet_writeback_target", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qc_review_decision_record_table",
        "qc_review_decision",
        ["record_table"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_record_id",
        "qc_review_decision",
        ["record_id"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_replicate_group_key",
        "qc_review_decision",
        ["replicate_group_key"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_resource_name",
        "qc_review_decision",
        ["resource_name"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_flag_type",
        "qc_review_decision",
        ["flag_type"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_decision_status",
        "qc_review_decision",
        ["decision_status"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_assigned_to_email",
        "qc_review_decision",
        ["assigned_to_email"],
        unique=False,
    )
    op.create_index(
        "ix_qc_review_decision_synced_to_gsheet",
        "qc_review_decision",
        ["synced_to_gsheet"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_qc_review_decision_synced_to_gsheet", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_assigned_to_email", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_decision_status", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_flag_type", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_resource_name", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_replicate_group_key", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_record_id", table_name="qc_review_decision")
    op.drop_index("ix_qc_review_decision_record_table", table_name="qc_review_decision")
    op.drop_table("qc_review_decision")
