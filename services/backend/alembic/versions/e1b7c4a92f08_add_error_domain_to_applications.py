"""add error_domain to applications

Revision ID: e1b7c4a92f08
Revises: 164269e26927
Create Date: 2026-07-14 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1b7c4a92f08"
down_revision: Union[str, Sequence[str], None] = "164269e26927"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("applications", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "error_domain",
                sa.Enum("MODEL", "SUBMISSION", name="errordomain"),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("applications", schema=None) as batch_op:
        batch_op.drop_column("error_domain")
