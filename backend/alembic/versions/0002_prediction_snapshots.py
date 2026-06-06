"""add prediction snapshots

Revision ID: 0002_prediction_snapshots
Revises: 0001_initial
Create Date: 2026-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_prediction_snapshots"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
        sa.Column("as_of_date", sa.Date(), nullable=False, index=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("probability_up", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("signal", sa.String(length=20), nullable=False),
        sa.Column("expected_return", sa.Float(), nullable=True),
        sa.Column("realized_return", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("symbol", "as_of_date", "horizon_days", name="uq_prediction_symbol_date_horizon"),
    )


def downgrade() -> None:
    op.drop_table("prediction_snapshots")
