"""add search settings

Revision ID: d0e2aab475d2
Revises: a7d2e891f4c3
Create Date: 2026-06-10 17:39:39.566426

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d0e2aab475d2"
down_revision: Union[str, Sequence[str], None] = "a7d2e891f4c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "max_pages",
                sa.Integer(),
                nullable=False,
                server_default="5",
            )
        )
        batch_op.add_column(
            sa.Column(
                "max_vacancies",
                sa.Integer(),
                nullable=False,
                server_default="50",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("max_vacancies")
        batch_op.drop_column("max_pages")
