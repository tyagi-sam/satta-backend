"""remove zerodha api credentials

Revision ID: remove_zerodha_api_credentials
Revises: cb9d37842b06
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_zerodha_api_credentials'
down_revision = 'cb9d37842b06'  # Points to the latest migration
branch_labels = None
depends_on = None

def upgrade():
    # Remove the columns
    op.drop_column('users', 'zerodha_api_key')
    op.drop_column('users', 'zerodha_api_secret')

def downgrade():
    # Add the columns back if needed to rollback
    op.add_column('users', sa.Column('zerodha_api_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('zerodha_api_secret', sa.String(), nullable=True)) 