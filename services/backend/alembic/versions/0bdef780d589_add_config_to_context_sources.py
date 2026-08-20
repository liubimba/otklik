from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0bdef780d589"
down_revision: Union[str, Sequence[str], None] = "9c2b056b24a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("context_sources", schema=None) as batch_op:
        batch_op.add_column(sa.Column("config", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("context_sources", schema=None) as batch_op:
        batch_op.drop_column("config")
