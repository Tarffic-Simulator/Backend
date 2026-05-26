"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("username", sa.String(50), unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
    )
    op.create_table(
        "saved_simulations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("engine_simulation_id", sa.String(100), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "engine_simulation_id", name="uq_user_simulation"),
    )


def downgrade() -> None:
    op.drop_table("saved_simulations")
    op.drop_table("users")
