"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-06-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'active'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "astro_measurements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("body", sa.String(length=50), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.UniqueConstraint("date", "body", name="uq_astro_date_body"),
    )
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.UniqueConstraint("date", "symbol", name="uq_market_date_symbol"),
    )
    op.create_table(
        "cycle_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("body_a", sa.String(length=50), nullable=False),
        sa.Column("body_b", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("cycle_candidates")
    op.drop_table("market_prices")
    op.drop_table("astro_measurements")
    op.drop_table("subscriptions")
    op.drop_table("users")
