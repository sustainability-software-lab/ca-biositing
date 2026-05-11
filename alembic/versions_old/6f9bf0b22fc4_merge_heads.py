"""merge heads

Revision ID: 6f9bf0b22fc4
Revises: 97a23076c0d9, 17fab0e1d312
Create Date: 2026-02-23 21:38:13.716312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f9bf0b22fc4'
down_revision: Union[str, Sequence[str], None] = ('97a23076c0d9', '17fab0e1d312')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
