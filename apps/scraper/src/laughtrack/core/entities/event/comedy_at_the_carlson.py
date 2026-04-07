"""
Comedy @ The Carlson event data model.

Thin subclass of OvationTixEvent — all ticket extraction, date parsing,
and Show conversion logic lives in the shared base.
"""

from dataclasses import dataclass

from laughtrack.core.entities.event.ovationtix import OvationTixEvent


@dataclass
class ComedyAtTheCarlsonEvent(OvationTixEvent):
    """A single upcoming performance from the OvationTix API for Comedy @ The Carlson."""

    pass
