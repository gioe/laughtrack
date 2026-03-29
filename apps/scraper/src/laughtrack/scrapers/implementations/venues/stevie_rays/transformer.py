"""Stevie Ray's event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.stevie_rays import StevieRaysEvent


class StevieRaysEventTransformer(DataTransformer[StevieRaysEvent]):
    pass
