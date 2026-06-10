"""add_community_sharing_fields

Revision ID: 9d4e5f678901
Revises: 8c9d3e4f5678
Create Date: 2026-06-10 14:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d4e5f678901"
down_revision: Union[str, Sequence[str], None] = "8c9d3e4f5678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_shared, shared_at, and share_anonymous columns to loker_checks table."""
    # Add is_shared boolean column with default False
    op.add_column(
        "loker_checks",
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false")
    )
    
    # Add shared_at datetime column for share timestamp
    op.add_column(
        "loker_checks",
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add share_anonymous boolean column with default False
    op.add_column(
        "loker_checks",
        sa.Column("share_anonymous", sa.Boolean(), nullable=False, server_default="false")
    )
    
    # Add index on is_shared for query optimization
    op.create_index(
        op.f("ix_loker_checks_is_shared"),
        "loker_checks",
        ["is_shared"],
        unique=False
    )


def downgrade() -> None:
    """Remove is_shared, shared_at, and share_anonymous columns from loker_checks table."""
    op.drop_index(op.f("ix_loker_checks_is_shared"), table_name="loker_checks")
    op.drop_column("loker_checks", "share_anonymous")
    op.drop_column("loker_checks", "shared_at")
    op.drop_column("loker_checks", "is_shared")