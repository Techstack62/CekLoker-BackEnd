"""add_profile_image_to_users

Revision ID: 7a2b5c8d1234
Revises: 3f9026ea7493
Create Date: 2026-06-10 13:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a2b5c8d1234'
down_revision: Union[str, Sequence[str], None] = '3f9026ea7493'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile_image column to users table."""
    op.add_column('users', sa.Column('profile_image', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove profile_image column from users table."""
    op.drop_column('users', 'profile_image')