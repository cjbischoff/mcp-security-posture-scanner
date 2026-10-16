"""drop unique constraint on scan_targets.name

Targets are identified by full connection info, so two targets may share
a name.

Revision ID: 7c2d4e9a1b3f
Revises: 1689000e03f7
Create Date: 2026-10-16

"""
from typing import Sequence, Union

from alembic import op


revision: str = '7c2d4e9a1b3f'
down_revision: Union[str, Sequence[str], None] = '1689000e03f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLite reflects the original UNIQUE(name) unnamed; this convention names it.
# Postgres auto-named it scan_targets_name_key.
_SQLITE_NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _constraint_name() -> str:
    """Return the unique constraint's name for the current dialect."""
    if op.get_bind().dialect.name == "sqlite":
        return "uq_scan_targets_name"
    return "scan_targets_name_key"


def upgrade() -> None:
    """Drop the unique constraint on scan_targets.name."""
    with op.batch_alter_table("scan_targets", naming_convention=_SQLITE_NAMING) as batch:
        batch.drop_constraint(_constraint_name(), type_="unique")


def downgrade() -> None:
    """Restore the unique constraint on scan_targets.name."""
    with op.batch_alter_table("scan_targets") as batch:
        batch.create_unique_constraint(_constraint_name(), ["name"])
