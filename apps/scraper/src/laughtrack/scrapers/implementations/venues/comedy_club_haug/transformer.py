"""Comedy Club Haug event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent


class ComedyClubHaugEventTransformer(DataTransformer[ComedyClubHaugEvent]):
    pass
