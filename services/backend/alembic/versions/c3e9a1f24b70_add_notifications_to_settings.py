from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3e9a1f24b70"
down_revision: Union[str, Sequence[str], None] = "b7e3a1c95f24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "notifications",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("notifications")
