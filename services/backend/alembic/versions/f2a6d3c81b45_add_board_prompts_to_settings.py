from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a6d3c81b45"
down_revision: str | Sequence[str] | None = "d1f4a2b7c9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "board_prompts",
                sa.JSON(),
                nullable=False,
                server_default="{}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("board_prompts")
