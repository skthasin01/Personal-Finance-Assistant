"""users.is_demo for one-click demo workspaces

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.create_index("ix_users_is_demo_created", ["is_demo", "created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_is_demo_created")
        batch_op.drop_column("is_demo")
