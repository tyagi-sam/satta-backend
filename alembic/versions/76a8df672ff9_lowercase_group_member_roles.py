"""lowercase group member roles

Revision ID: 76a8df672ff9
Revises: fix_model_inconsistencies
Create Date: 2024-03-19 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76a8df672ff9'
down_revision: Union[str, None] = 'fix_model_inconsistencies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change role column to VARCHAR if it's an enum
    op.execute("ALTER TABLE group_members ALTER COLUMN role TYPE VARCHAR USING role::text;")
    # Update values to lowercase
    op.execute("UPDATE group_members SET role = LOWER(role) WHERE role IN ('LEADER', 'MEMBER')")
    # Drop the old enum type if it exists
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'memberrole') THEN DROP TYPE memberrole; END IF; END $$;")


def downgrade() -> None:
    # No-op for downgrade (restoring enum type is not trivial)
    pass
