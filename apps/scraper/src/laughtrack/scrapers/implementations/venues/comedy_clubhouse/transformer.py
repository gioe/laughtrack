"""The Comedy Clubhouse event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from laughtrack.core.entities.event.comedy_clubhouse import ComedyClubhouseEvent


class ComedyClubhouseEventTransformer(DataTransformer[ComedyClubhouseEvent]):
    pass
