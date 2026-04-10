"""Coral Gables Comedy Club event transformer."""

from laughtrack.core.entities.event.coral_gables_comedy_club import (
    CoralGablesComedyClubEvent,
)
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class CoralGablesComedyClubEventTransformer(
    DataTransformer[CoralGablesComedyClubEvent]
):
    pass
