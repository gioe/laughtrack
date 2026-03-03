"""Infrastructure implementation of the database port protocol."""

from laughtrack.ports.database import DatabaseConnection


class DatabaseAdapter(DatabaseConnection):
    def create_connection(self, autocommit: bool = True):
        from .connection import create_connection as _create

        return _create(autocommit=autocommit)

    def create_connection_with_transaction(self):
        from .connection import create_connection_with_transaction as _create_tx

        return _create_tx()

    def get_connection(self, autocommit: bool = True):
        from .connection import get_connection as _get

        return _get(autocommit=autocommit)

    def get_transaction(self):
        from .connection import get_transaction as _get_tx

        return _get_tx()


# Default instance for wiring
default_db: DatabaseConnection = DatabaseAdapter()
