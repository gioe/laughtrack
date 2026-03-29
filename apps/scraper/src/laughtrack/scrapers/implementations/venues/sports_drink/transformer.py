"""Sports Drink event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.sports_drink import SportsDrinkEvent


class SportsDrinkEventTransformer(DataTransformer[SportsDrinkEvent]):
    pass
