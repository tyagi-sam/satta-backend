"""fix model inconsistencies

Revision ID: fix_model_inconsistencies
Revises: 832b8ce41bd1
Create Date: 2024-03-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'fix_model_inconsistencies'
down_revision = '832b8ce41bd1'
branch_labels = None
depends_on = None

def column_exists(table_name, column_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():
    # Add missing columns to groups table
    if not column_exists('groups', 'created_by'):
        op.add_column('groups', sa.Column('created_by', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_groups_created_by_users',
            'groups', 'users',
            ['created_by'], ['id']
        )
    
    # Add missing columns to group_members table
    if not column_exists('group_members', 'is_active'):
        op.add_column('group_members', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    if not column_exists('group_members', 'joined_at'):
        op.add_column('group_members', sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    
    # Add missing columns to users table
    if not column_exists('users', 'name'):
        op.add_column('users', sa.Column('name', sa.String(), nullable=True))
    if not column_exists('users', 'zerodha_user_id'):
        op.add_column('users', sa.Column('zerodha_user_id', sa.String(), nullable=True))
    if not column_exists('users', 'zerodha_access_token'):
        op.add_column('users', sa.Column('zerodha_access_token', sa.String(), nullable=True))
    if not column_exists('users', 'zerodha_refresh_token'):
        op.add_column('users', sa.Column('zerodha_refresh_token', sa.String(), nullable=True))
    if not column_exists('users', 'zerodha_token_expiry'):
        op.add_column('users', sa.Column('zerodha_token_expiry', sa.DateTime(timezone=True), nullable=True))
    if not column_exists('users', 'is_active'):
        op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    if not column_exists('users', 'is_superuser'):
        op.add_column('users', sa.Column('is_superuser', sa.Boolean(), server_default='false', nullable=False))
    if not column_exists('users', 'preferences'):
        op.add_column('users', sa.Column('preferences', sa.Text(), nullable=True))
    
    # Create indexes if they don't exist
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_zerodha_user_id' not in indexes:
        op.create_index(op.f('ix_users_zerodha_user_id'), 'users', ['zerodha_user_id'], unique=True)
    
    indexes = [idx['name'] for idx in inspector.get_indexes('groups')]
    if 'ix_groups_created_by' not in indexes:
        op.create_index(op.f('ix_groups_created_by'), 'groups', ['created_by'], unique=False)

def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_groups_created_by'), table_name='groups')
    op.drop_index(op.f('ix_users_zerodha_user_id'), table_name='users')
    
    # Drop columns from users table
    if column_exists('users', 'preferences'):
        op.drop_column('users', 'preferences')
    if column_exists('users', 'is_superuser'):
        op.drop_column('users', 'is_superuser')
    if column_exists('users', 'is_active'):
        op.drop_column('users', 'is_active')
    if column_exists('users', 'zerodha_token_expiry'):
        op.drop_column('users', 'zerodha_token_expiry')
    if column_exists('users', 'zerodha_refresh_token'):
        op.drop_column('users', 'zerodha_refresh_token')
    if column_exists('users', 'zerodha_access_token'):
        op.drop_column('users', 'zerodha_access_token')
    if column_exists('users', 'zerodha_user_id'):
        op.drop_column('users', 'zerodha_user_id')
    if column_exists('users', 'name'):
        op.drop_column('users', 'name')
    
    # Drop columns from group_members table
    if column_exists('group_members', 'joined_at'):
        op.drop_column('group_members', 'joined_at')
    if column_exists('group_members', 'is_active'):
        op.drop_column('group_members', 'is_active')
    
    # Drop columns from groups table
    if column_exists('groups', 'created_by'):
        op.drop_constraint('fk_groups_created_by_users', 'groups', type_='foreignkey')
        op.drop_column('groups', 'created_by') 