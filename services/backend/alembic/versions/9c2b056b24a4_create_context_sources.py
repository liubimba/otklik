from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9c2b056b24a4"
down_revision: Union[str, Sequence[str], None] = "a7f3d2c81b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "context_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "kind", sa.Enum("GITHUB", "WEB", name="contextsourcekind"), nullable=False
        ),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "OK", "ERROR", name="contextsourcestatus"),
            nullable=False,
        ),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_context_sources")),
    )


def downgrade() -> None:
    op.drop_table("context_sources")
