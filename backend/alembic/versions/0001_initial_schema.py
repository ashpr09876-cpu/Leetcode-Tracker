"""Initial schema.

Baseline migration: it creates the tables from the models as they were when the project was first
generated. NOTE: it was written without access to a live PostgreSQL server; run
`alembic upgrade head` once and then `alembic check` to confirm no drift. For every later schema change,
use `alembic revision --autogenerate -m "..."` so changes are captured as explicit operations.
"""
from alembic import op

from app import models  # noqa: F401
from app.db.session import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
