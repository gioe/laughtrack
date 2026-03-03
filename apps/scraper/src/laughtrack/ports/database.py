"""Database-related protocols exposed via ports.

Defines the minimal connection/transaction contract and re-exports the
`DatabaseEntity` protocol used by handlers.
"""

from typing import Protocol, runtime_checkable

from laughtrack.foundation.protocols.database_entity import DatabaseEntity  # noqa: F401


@runtime_checkable
class DatabaseConnection(Protocol):
	"""Protocol describing connection helpers exposed via the DB adapter."""

	def create_connection(self, autocommit: bool = True):  # -> connection
		...

	def create_connection_with_transaction(self):  # -> connection
		...

	def get_connection(self, autocommit: bool = True):  # -> contextmanager[connection]
		...

	def get_transaction(self):  # -> contextmanager[connection]
		...
