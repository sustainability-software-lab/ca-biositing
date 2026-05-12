"""merge multiple heads

Revision ID: 2605c6e2b9da
Revises: 6f9bf0b22fc4, eacbc6544a10
Create Date: 2026-02-26 16:10:21.112443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2605c6e2b9da'
down_revision: Union[str, Sequence[str], None] = ('6f9bf0b22fc4', 'eacbc6544a10')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
