"""search_vacancies association table (M2M between searches and vacancies)

Revision ID: a8c4f2d1e7b3
Revises: e5f9c1a273b4
Create Date: 2026-06-14 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c4f2d1e7b3"
down_revision: Union[str, Sequence[str], None] = "e5f9c1a273b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_vacancies",
        sa.Column(
            "search_id",
            sa.String(),
            sa.ForeignKey("searches.id"),
            primary_key=True,
        ),
        sa.Column(
            "vacancy_id",
            sa.Integer(),
            sa.ForeignKey("vacancies.id"),
            primary_key=True,
        ),
    )
    op.execute(
        """
        INSERT OR IGNORE INTO search_vacancies (search_id, vacancy_id)
        SELECT search_id, id FROM vacancies WHERE search_id IS NOT NULL
        """
    )
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.drop_index("ix_vacancies_search_id")
        batch_op.drop_constraint("fk_vacancies_search_id_searches", type_="foreignkey")
        batch_op.drop_column("search_id")


def downgrade() -> None:
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("search_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_vacancies_search_id_searches",
            "searches",
            ["search_id"],
            ["id"],
        )
        batch_op.create_index("ix_vacancies_search_id", ["search_id"])
    op.execute(
        """
        UPDATE vacancies SET search_id = (
            SELECT search_id FROM search_vacancies
            WHERE vacancy_id = vacancies.id LIMIT 1
        )
        """
    )
    op.drop_table("search_vacancies")
