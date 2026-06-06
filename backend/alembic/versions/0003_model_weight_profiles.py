"""add model weight profiles

Revision ID: 0003_model_weight_profiles
Revises: 0002_prediction_snapshots
Create Date: 2026-06-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_model_weight_profiles"
down_revision = "0002_prediction_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_weight_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("hit_rate", sa.Float(), nullable=False),
        sa.Column("average_signal_return", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False, server_default="correlation_learning"),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("symbol", "horizon_days", name="uq_weight_profile_symbol_horizon"),
    )


def downgrade() -> None:
    op.drop_table("model_weight_profiles")
