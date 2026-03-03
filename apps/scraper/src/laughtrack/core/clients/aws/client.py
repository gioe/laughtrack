from typing import List

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.models.types import JSONDict


class AWSClient(BaseApiClient):
    """Client for AWS buckets."""

    def __init__(self, club: Club):
        super().__init__(club)

    def _build_s3_url(self, domain: str, path: str = "") -> str:
        """
        Build S3 URL for a given domain and path.

        Args:
            domain: The S3 bucket domain (without .s3.amazonaws.com)
            path: Optional path within the bucket

        Returns:
            Complete S3 URL
        """
        base_url = f"https://{domain}.s3.amazonaws.com"
        if path:
            # Ensure path doesn't start with slash to avoid double slashes
            path = path.lstrip("/")
            return f"{base_url}/{path}"
        return f"{base_url}/"

    async def fetch_bucket_contents(self, domain: str, path: str) -> List[JSONDict]:
        """
        Fetch contents from an S3 bucket.

        Args:
            domain: The S3 bucket domain (without .s3.amazonaws.com)
            path: The path within the bucket

        Returns:
            List of dictionaries containing bucket contents

        Raises:
            Exception: If the request fails or returns invalid data
        """
        url = self._build_s3_url(domain, path)

        try:
            json_data = await self.fetch_json(url=url, logger_context={"domain": domain, "path": path})

            if json_data is None:
                self.log_error("Failed to fetch valid JSON data")
                raise Exception("Failed to fetch valid JSON data")

            # Ensure we return a list
            if isinstance(json_data, list):
                return json_data
            elif isinstance(json_data, dict):
                # If it's a single object, wrap in a list
                return [json_data]
            else:
                # If it's neither list nor dict, return as content
                return [{"content": str(json_data)}]

        except Exception as e:
            error_msg = f"Failed to fetch bucket contents from {url}: {str(e)}"
            self.log_error(error_msg)
            raise Exception(error_msg)
