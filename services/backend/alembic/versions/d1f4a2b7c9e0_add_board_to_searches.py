from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1f4a2b7c9e0"
down_revision: str | Sequence[str] | None = "c3e9a1f24b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("searches", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "board",
                sa.String(),
                nullable=False,
                server_default="hh_ru",
            )
        )
        batch_op.create_index("ix_searches_board", ["board"])


def downgrade() -> None:
    with op.batch_alter_table("searches", schema=None) as batch_op:
        batch_op.drop_index("ix_searches_board")
        batch_op.drop_column("board")
