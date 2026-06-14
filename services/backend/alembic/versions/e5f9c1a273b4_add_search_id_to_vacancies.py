"""add search_id to vacancies

Revision ID: e5f9c1a273b4
Revises: d0e2aab475d2
Create Date: 2026-06-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f9c1a273b4"
down_revision: Union[str, Sequence[str], None] = "d0e2aab475d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("search_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_vacancies_search_id_searches",
            "searches",
            ["search_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_vacancies_search_id",
            ["search_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.drop_index("ix_vacancies_search_id")
        batch_op.drop_constraint("fk_vacancies_search_id_searches", type_="foreignkey")
        batch_op.drop_column("search_id")
