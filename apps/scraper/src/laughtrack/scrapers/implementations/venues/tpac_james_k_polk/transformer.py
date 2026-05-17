"""Event transformer for TPAC James K. Polk Theater."""

from laughtrack.core.entities.event.tpac_james_k_polk import TpacJamesKPolkEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TpacJamesKPolkEventTransformer(DataTransformer[TpacJamesKPolkEvent]):
    """Transforms TPAC James K. Polk Theater events into Show objects."""
