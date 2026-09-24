from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c1e5d92f34"
down_revision: str | Sequence[str] | None = "f2a6d3c81b45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "kwork_price_percent",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("kwork_price_percent")
