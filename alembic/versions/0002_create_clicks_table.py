"""create clicks table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clicks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("short_code", sa.String(length=32), nullable=False),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_clicks_short_code", "clicks", ["short_code"])
    op.create_index("ix_clicks_code_time", "clicks", ["short_code", "clicked_at"])


def downgrade() -> None:
    op.drop_index("ix_clicks_code_time", table_name="clicks")
    op.drop_index("ix_clicks_short_code", table_name="clicks")
    op.drop_table("clicks")
