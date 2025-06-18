"""add zerodha token expiry

Revision ID: add_zerodha_token_expiry
Revises: create_notification_tables
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_zerodha_token_expiry'
down_revision: Union[str, None] = 'create_notification_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add zerodha_token_expiry column to users table
    op.add_column('users', sa.Column('zerodha_token_expiry', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove zerodha_token_expiry column from users table
    op.drop_column('users', 'zerodha_token_expiry') 