from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7f3d2c81b40"
down_revision: Union[str, Sequence[str], None] = "e1b7c4a92f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("llm_proxy_url", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_column("llm_proxy_url")
