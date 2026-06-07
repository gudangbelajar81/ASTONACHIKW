"""add user app states

Revision ID: 0004_user_app_states
Revises: 0003_model_weight_profiles
Create Date: 2026-06-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_user_app_states"
down_revision = "0003_model_weight_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_app_states",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_app_states")
