"""Database adapter facade.

Re-exports infrastructure database connection helpers as the stable adapter API,
and provides a protocol-compliant adapter object for injection.
"""

from laughtrack.infrastructure.database.connection import (  # noqa: F401
	create_connection,
	create_connection_with_transaction,
	get_connection,
	get_transaction,
)

from laughtrack.ports.database import DatabaseConnection


class _DbAdapter(DatabaseConnection):
	def create_connection(self, autocommit: bool = True):
		from laughtrack.infrastructure.database.connection import create_connection as _create

		return _create(autocommit=autocommit)

	def create_connection_with_transaction(self):
		from laughtrack.infrastructure.database.connection import create_connection_with_transaction as _create_tx

		return _create_tx()

	def get_connection(self, autocommit: bool = True):
		from laughtrack.infrastructure.database.connection import get_connection as _get

		return _get(autocommit=autocommit)

	def get_transaction(self):
		from laughtrack.infrastructure.database.connection import get_transaction as _get_tx

		return _get_tx()


# Export default adapter instance
db: DatabaseConnection = _DbAdapter()

# Self-register into the core.data.base_handler seam: core cannot import the
# adapters layer (core.entities import-linter contract), so the concrete
# adapter binds itself whenever this module loads. scripts/__init__.py and
# laughtrack.app.wiring both import this module, covering every entry-point
# family (TASK-3701). Imported at the bottom to keep the edge acyclic:
# base_handler imports only ports/foundation, never adapters.
from laughtrack.core.data.base_handler import configure_database as _configure_base_handler_db

_configure_base_handler_db(db)
