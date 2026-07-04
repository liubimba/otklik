"""drop vacancies.response_link — dead column

Revision ID: c1e5b8f92a04
Revises: a8c4f2d1e7b3
Create Date: 2026-07-02 12:00:00.000000

Introduced in 9a8f1a647612 as an optional URL, but the hh.ru parser only
ever wrote button *text* into it (not a URL) and nobody read it as one.
The LetterSendingWorker used to pass it to writer.submit(vacancy_url=…),
which crashed Playwright on "Cannot navigate to invalid URL". Fixed
2026-07-02 by switching the worker to vacancy.apply_link. This migration
finishes the cleanup by removing the column entirely.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e5b8f92a04"
down_revision: Union[str, Sequence[str], None] = "a8c4f2d1e7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("vacancies", "response_link")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("vacancies", sa.Column("response_link", sa.String(), nullable=True))
