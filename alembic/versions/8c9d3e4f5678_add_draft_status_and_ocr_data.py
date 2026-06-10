"""add_draft_status_and_ocr_data

Revision ID: 8c9d3e4f5678
Revises: 7a2b5c8d1234
Create Date: 2026-06-10 14:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c9d3e4f5678"
down_revision: Union[str, Sequence[str], None] = "7a2b5c8d1234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ocr_data, is_draft, and submitted_at columns to loker_checks table."""
    # Add ocr_data JSON column for structured OCR results
    op.add_column(
        "loker_checks",
        sa.Column("ocr_data", sa.JSON(), nullable=True)
    )
    
    # Add is_draft boolean column with default True
    op.add_column(
        "loker_checks",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="true")
    )
    
    # Add submitted_at datetime column for submission timestamp
    op.add_column(
        "loker_checks",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add index on is_draft for query optimization
    op.create_index(
        op.f("ix_loker_checks_is_draft"),
        "loker_checks",
        ["is_draft"],
        unique=False
    )


def downgrade() -> None:
    """Remove ocr_data, is_draft, and submitted_at columns from loker_checks table."""
    op.drop_index(op.f("ix_loker_checks_is_draft"), table_name="loker_checks")
    op.drop_column("loker_checks", "submitted_at")
    op.drop_column("loker_checks", "is_draft")
    op.drop_column("loker_checks", "ocr_data")