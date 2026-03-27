"""Event transformer for Zanies Comedy Club."""

from laughtrack.core.entities.event.zanies import ZaniesEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ZaniesEventTransformer(DataTransformer[ZaniesEvent]):
    """Transforms ZaniesEvent objects into Show domain objects."""
