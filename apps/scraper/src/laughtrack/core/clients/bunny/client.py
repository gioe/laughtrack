"""Bunny CDN Storage API client for uploading comedian images."""

import os
from dataclasses import dataclass
from typing import Optional

import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class UploadResult:
    """Result of a Bunny CDN Storage upload."""

    success: bool
    status_code: int
    path: str
    message: str


class BunnyCDNStorageClient:
    """Client for uploading files to Bunny CDN Storage.

    Uses the Bunny CDN Storage API:
    PUT https://{region}.storage.bunnycdn.com/{zone}/{path}

    Requires env vars:
        BUNNYCDN_STORAGE_PASSWORD - API key for the storage zone
        BUNNYCDN_STORAGE_ZONE    - storage zone name
    """

    DEFAULT_REGION = "la"

    def __init__(
        self,
        storage_password: Optional[str] = None,
        storage_zone: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.storage_password = storage_password or os.environ.get("BUNNYCDN_STORAGE_PASSWORD", "")
        self.storage_zone = storage_zone or os.environ.get("BUNNYCDN_STORAGE_ZONE", "")
        self.region = region or os.environ.get("BUNNYCDN_STORAGE_REGION", self.DEFAULT_REGION)

        if not self.storage_password:
            raise ValueError("BUNNYCDN_STORAGE_PASSWORD is required")
        if not self.storage_zone:
            raise ValueError("BUNNYCDN_STORAGE_ZONE is required")

    def _build_url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"https://{self.region}.storage.bunnycdn.com/{self.storage_zone}/{path}"

    def upload(self, data: bytes, path: str, content_type: str = "image/png") -> UploadResult:
        """Upload file bytes to a path in the storage zone.

        Args:
            data: Raw file bytes to upload.
            path: Destination path within the zone (e.g. "comedians/joe-smith.png").
            content_type: MIME type of the file (default: image/png).

        Returns:
            UploadResult with success status and details.
        """
        url = self._build_url(path)
        headers = {
            "AccessKey": self.storage_password,
            "Content-Type": content_type,
        }

        try:
            response = requests.put(url, data=data, headers=headers, timeout=15)
            status = response.status_code

            if status == 201:
                Logger.info(f"Bunny CDN: uploaded {path} ({len(data)} bytes)")
                return UploadResult(success=True, status_code=status, path=path, message="Created")

            body = response.text

            if status == 401:
                Logger.error(f"Bunny CDN: auth failed for {path} (401)")
                return UploadResult(success=False, status_code=status, path=path, message="Authentication failed — check BUNNYCDN_STORAGE_PASSWORD")

            if status == 409:
                Logger.warning(f"Bunny CDN: conflict uploading {path} (409)")
                return UploadResult(success=False, status_code=status, path=path, message="Conflict — file may already exist")

            Logger.error(f"Bunny CDN: upload failed for {path} — HTTP {status}: {body[:200]}")
            return UploadResult(success=False, status_code=status, path=path, message=f"HTTP {status}: {body[:200]}")

        except requests.RequestException as e:
            Logger.error(f"Bunny CDN: network error uploading {path} — {e}")
            return UploadResult(success=False, status_code=0, path=path, message=f"Network error: {e}")
