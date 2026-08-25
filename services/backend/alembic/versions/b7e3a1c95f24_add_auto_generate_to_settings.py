from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3a1c95f24"
down_revision: Union[str, Sequence[str], None] = "0bdef780d589"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_generate",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.execute("UPDATE settings SET auto_generate = auto_submit")


def downgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("auto_generate")
