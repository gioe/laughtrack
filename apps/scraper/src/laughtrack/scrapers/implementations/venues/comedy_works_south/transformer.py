"""Comedy Works South data transformation utilities.

ComedyWorksDowntownEvent implements ShowConvertible, so the base
DataTransformer.transform_to_show() delegates to event.to_show(club)
automatically — no override needed.
"""

from laughtrack.core.entities.event.comedy_works_downtown import ComedyWorksDowntownEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyWorksSouthTransformer(DataTransformer[ComedyWorksDowntownEvent]):
    """Transform ComedyWorksDowntownEvent objects to Show objects."""

    pass
