"""Merge multiple heads

Revision ID: 64de60aff03d
Revises: d3f1e2a4b5c6, ec0865c36f55
Create Date: 2026-03-05 09:19:51.181996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64de60aff03d'
down_revision: Union[str, Sequence[str], None] = ('d3f1e2a4b5c6', 'ec0865c36f55')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
