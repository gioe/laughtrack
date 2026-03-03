from dataclasses import dataclass
from typing import Dict, Optional

from laughtrack.foundation.models.types import JSONDict


@dataclass
class RequestData:
    """Data model for HTTP request information."""

    url: str
    method: str = "GET"
    payload: Optional[JSONDict] = None
    headers: Optional[Dict[str, str]] = None

    def to_tuple(self) -> tuple[str, Optional[JSONDict], str, Optional[Dict[str, str]]]:
        """Convert the request data to a tuple format for backward compatibility."""
        return (self.url, self.payload, self.method, self.headers)

    @classmethod
    def from_tuple(cls, data: tuple[str, Optional[JSONDict], str, Optional[Dict[str, str]]]) -> "RequestData":
        """Create a RequestData instance from a tuple."""
        return cls(url=data[0], payload=data[1], method=data[2], headers=data[3])

    @classmethod
    def get(cls, url: str, headers: Optional[Dict[str, str]] = None) -> "RequestData":
        """Create a GET request."""
        return cls(url=url, method="GET", headers=headers)

    @classmethod
    def post(
        cls, url: str, payload: Optional[JSONDict] = None, headers: Optional[Dict[str, str]] = None
    ) -> "RequestData":
        """Create a POST request."""
        return cls(url=url, method="POST", payload=payload, headers=headers)

    def with_headers(self, headers: Dict[str, str]) -> "RequestData":
        """Create a new instance with updated headers."""
        return RequestData(url=self.url, method=self.method, payload=self.payload, headers=headers)

    def with_payload(self, payload: JSONDict) -> "RequestData":
        """Create a new instance with updated payload."""
        return RequestData(url=self.url, method=self.method, payload=payload, headers=self.headers)
