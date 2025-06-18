"""add is_superuser to users

Revision ID: 832b8ce41bd1
Revises: add_zerodha_token_expiry
Create Date: 2024-03-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '832b8ce41bd1'
down_revision: Union[str, None] = 'add_zerodha_token_expiry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('users', 'is_superuser')
