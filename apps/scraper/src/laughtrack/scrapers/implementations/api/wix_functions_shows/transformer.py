"""Wix/Velo _functions/shows event transformer."""

from laughtrack.core.entities.event.wix_functions_shows import WixFunctionsShowEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class WixFunctionsShowEventTransformer(DataTransformer[WixFunctionsShowEvent]):
    pass
