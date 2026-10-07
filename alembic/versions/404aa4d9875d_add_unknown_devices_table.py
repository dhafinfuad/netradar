"""Add unknown_devices table

Revision ID: 404aa4d9875d
Revises: 5ab6b3f2efa1
Create Date: 2026-07-23 16:41:10.009473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '404aa4d9875d'
down_revision: Union[str, Sequence[str], None] = '5ab6b3f2efa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('unknown_devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ip_address', sa.String(length=50), nullable=False),
    sa.Column('mac_address', sa.String(length=50), nullable=True),
    sa.Column('vendor', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('first_seen', sa.DateTime(), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unknown_devices_id'), 'unknown_devices', ['id'], unique=False)
    op.create_index(op.f('ix_unknown_devices_ip_address'), 'unknown_devices', ['ip_address'], unique=False)
    op.create_index(op.f('ix_unknown_devices_mac_address'), 'unknown_devices', ['mac_address'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_unknown_devices_mac_address'), table_name='unknown_devices')
    op.drop_index(op.f('ix_unknown_devices_ip_address'), table_name='unknown_devices')
    op.drop_index(op.f('ix_unknown_devices_id'), table_name='unknown_devices')
    op.drop_table('unknown_devices')
