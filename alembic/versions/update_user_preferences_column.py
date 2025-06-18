"""update user preferences column

Revision ID: update_user_preferences_column
Revises: fix_model_inconsistencies
Create Date: 2024-03-18 03:20:28.732295

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_user_preferences_column'
down_revision = 'fix_model_inconsistencies'
branch_labels = None
depends_on = None

def upgrade():
    # Convert the column to JSON type
    op.execute('ALTER TABLE users ALTER COLUMN preferences TYPE jsonb USING preferences::jsonb')

def downgrade():
    # Convert back to text type
    op.execute('ALTER TABLE users ALTER COLUMN preferences TYPE text USING preferences::text') 