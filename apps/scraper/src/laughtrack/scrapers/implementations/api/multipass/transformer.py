"""Multipass event transformer (delegates to MultipassEvent.to_show)."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.multipass import MultipassEvent


class MultipassEventTransformer(DataTransformer[MultipassEvent]):
    pass
