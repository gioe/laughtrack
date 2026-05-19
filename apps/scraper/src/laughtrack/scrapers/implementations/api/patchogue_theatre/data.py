"""Page data container for the Patchogue Theatre scraper.

Re-exports the shared :class:`OvationTixPageData` from the generic OvationTix
implementation so the transformer pipeline binds on a single container type
(no duplicate dataclass instances ever flow through the same transformer
registry).
"""

from laughtrack.scrapers.implementations.api.ovationtix.data import OvationTixPageData

__all__ = ["OvationTixPageData"]
