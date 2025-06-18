"""add_password_field_to_user

Revision ID: a82d769ae3b3
Revises: 76e2808589be
Create Date: 2024-03-14 12:34:56.789012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.core.security import get_password_hash


# revision identifiers, used by Alembic.
revision: str = 'a82d769ae3b3'
down_revision: Union[str, None] = '76e2808589be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary column first
    op.add_column('users', sa.Column('temp_password', sa.String(), nullable=True))
    
    # Update existing users with a default hashed password
    default_password = get_password_hash("changeme123")
    op.execute(f"UPDATE users SET temp_password = '{default_password}'")
    
    # Add the final password column as non-nullable
    op.add_column('users', sa.Column('password', sa.String(), server_default=default_password, nullable=False))
    
    # Copy data from temp to final column if needed
    op.execute("UPDATE users SET password = temp_password")
    
    # Drop the temporary column
    op.drop_column('users', 'temp_password')


def downgrade() -> None:
    op.drop_column('users', 'password')
