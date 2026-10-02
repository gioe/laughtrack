"""Conservative Gotham poster caption OCR, restricted to two documented layouts.

OCR supplies printed text, never face identities. Every accepted caption must also
be corroborated against an existing canonical comedian by the caller. Unsupported
layouts and unavailable OCR/database services leave lineups unknown.
"""
import asyncio
import csv
import hashlib
import io
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps
from laughtrack.foundation.infrastructure.logger.logger import Logger

MAX_ASSETS = 32
MAX_BYTES = 5_000_000
MAX_PIXELS = 4_000_000


def asset_url(event):
    value = ((event._raw_data or {}).get("fieldData") or {}).get("event-image-url", "")
    if not isinstance(value, str):
        return ""
    value = "https:" + value if value.startswith("//") else value
    parts = urlsplit(value)
    return value if parts.scheme == "https" and parts.netloc == "sc-events.s3.amazonaws.com" else ""


def normalize_caption(value):
    return " ".join(re.sub(r"[^\w\s]", "", value.casefold()).split())


def event_room(event):
    return "vintage" if "vintage lounge" in event.name.casefold() else "main"


@dataclass(frozen=True)
class PosterText:
    layout: str
    date: str
    brand: str
    room: str
    captions: tuple[str, ...]

    def matches(self, event):
        date = event.start_datetime
        if date is None:
            return False
        date = date.astimezone(ZoneInfo("America/New_York"))
        if "COMEDY CLUB" not in self.brand.upper():
            return False
        if self.layout == "square" and not any(
                marker in self.room.upper() for marker in ("VINTAGE LOUNGE", "COMEDY CLUB")):
            return False
        vintage = "VINTAGE LOUNGE" in self.room.upper()
        if vintage != (event_room(event) == "vintage"):
            return False
        text = self.date.upper()
        # Full date, weekday and time are mandatory; a printed year, if any,
        # must agree. Never repair an OCR digit by guessing from the event.
        years = re.findall(r"\b20\d{2}\b", text)
        if years and any(int(year) != date.year for year in years):
            return False
        weekday = re.search(r"\b(MON|TUE|WED|THU|FRI|SAT|SUN)[A-Z]*\b", text)
        time = re.search(r"(?:@\s*)?(\d{1,2})(?::(\d{2}))?\s*([AP])M\b", text)
        if not weekday or weekday[1] != date.strftime("%a").upper() or not time:
            return False
        if not 1 <= int(time[1]) <= 12:
            return False
        hour = int(time[1]) % 12 + (12 if time[3] == "P" else 0)
        if (hour, int(time[2] or 0)) != (date.hour, date.minute):
            return False
        numeric = re.search(r"\b(\d{1,2})/(\d{1,2})\b", text)
        if numeric:
            return (int(numeric[1]), int(numeric[2])) == (date.month, date.day)
        named = re.search(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+(\d{1,2})", text)
        return bool(named and named[1] == date.strftime("%b").upper() and int(named[2]) == date.day)


def _read_crop(image, box, *, angle=0, fill="black", pad=True, min_confidence=25):
    w, h = image.size
    crop = image.crop(tuple(int(v * d) for v, d in zip(box, (w, h, w, h))))
    if angle:
        crop = crop.rotate(angle, expand=True, fillcolor=fill)
    crop = ImageOps.autocontrast(ImageOps.grayscale(crop))
    crop = ImageOps.invert(crop.resize((crop.width * 3, crop.height * 3)))
    if pad:
        crop = ImageOps.expand(crop, border=30, fill="white")
    data = io.BytesIO()
    crop.save(data, format="PNG")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", "6", "tsv"],
        input=data.getvalue(), capture_output=True, timeout=3, check=True,
    )
    rows = csv.DictReader(io.StringIO(result.stdout.decode()), delimiter="\t")
    return " ".join(row["text"].strip() for row in rows
                    if row["text"].strip() and float(row["conf"]) >= min_confidence)


def read_poster(data):
    """Read only date, branding, room and printed caption rectangles."""
    if len(data) > MAX_BYTES or not shutil.which("tesseract"):
        return None
    with Image.open(io.BytesIO(data)) as raw:
        if raw.width * raw.height > MAX_PIXELS or min(raw.size) < 500:
            return None
        image = raw.convert("RGB")
    ratio = image.width / image.height
    if .8 <= ratio <= .9:
        date = _read_crop(image, (.07, .468, .93, .55))
        brand = _read_crop(image, (330/960, 470/1133, 660/960, 516/1133), pad=False)
        boxes = [(.18, .55, .39, .635), (.43, .55, .61, .635), (.65, .55, .83, .635)]
        room, layout = "", "spotlight"
    elif .95 <= ratio <= 1.05:
        room = _read_crop(image, (.36, .435, .64, .603))
        vintage = "VINTAGE" in room.upper()
        date = _read_crop(image, (0, .43, .29, .62), angle=-13,
                          fill=(115, 115, 115) if vintage else "black")
        brand = _read_crop(image, (.72, .548, .96, .597) if vintage else (.32, .525, .65, .586))
        boxes = [(.02, .31, .35, .41), (.38, .31, .64, .41), (.66, .31, .99, .41)]
        boxes += [(.17, .891, .45, .979), (.55, .891, .85, .979)] if vintage else [(.17, .885, .46, .974)]
        layout = "square"
    else:
        return None
    # Reject generic/headshot templates before spending OCR work on captions.
    if "COMEDY CLUB" not in brand.upper() or not re.search(r"\d.*[AP]M", date.upper()):
        return None
    captions = []
    for box in boxes:
        text = _read_crop(image, box, min_confidence=0)
        # Remove isolated punctuation, but never repair/substitute letters.
        words = [word for word in text.split() if re.search(r"[A-Za-z]", word)]
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z]+(?:[.’'-][A-Za-z]+)*\.?", word) for word in words):
            name = " ".join(words)
            if not re.search(r"\b(TBA|MORE|COMEDY|CLUB|GOTHAM|GOTHAN|HOST|SPECIAL|GUEST)\b", name, re.I):
                captions.append(name)
    return PosterText(layout, date, brand, room, tuple(captions))


class PosterReader:
    """One run's bounded URL/content caches, including negative results."""
    def __init__(self, get_session):
        self.get_session = get_session
        self.urls = {}
        self.hashes = {}
        self.deadline = time.monotonic() + 120

    async def fetch(self, url):
        if url in self.urls:
            return self.urls[url]
        if len(self.urls) >= MAX_ASSETS or time.monotonic() >= self.deadline:
            return None
        self.urls[url] = None
        try:
            session = await self.get_session()
            async with session.stream("GET", url, timeout=10, allow_redirects=False) as response:
                if response.status_code != 200 or not response.headers.get("content-type", "").startswith("image/"):
                    Logger.debug(f"Gotham poster rejected HTTP status/content type: {response.status_code}")
                    return None
                data = bytearray()
                async for chunk in response.aiter_content():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        Logger.debug("Gotham poster exceeds image byte limit")
                        return None
            digest = hashlib.sha256(data).hexdigest()
            self.urls[url] = (digest, bytes(data))
        except Exception as exc:
            Logger.debug(f"Gotham poster download unavailable: {type(exc).__name__}")
        return self.urls[url]

    async def read(self, digest, data):
        if time.monotonic() >= self.deadline:
            return None
        if digest not in self.hashes:
            self.hashes[digest] = None
            try:
                self.hashes[digest] = await asyncio.to_thread(read_poster, data)
            except Exception as exc:
                Logger.debug(f"Gotham poster OCR unavailable: {type(exc).__name__}")
        return self.hashes[digest]

    async def enrich(self, events, corroborate):
        from laughtrack.core.clients.gotham.models.models import _explicit_billed_names
        grouped = {}
        for event in events:
            url = asset_url(event)
            if url:
                grouped.setdefault(url, []).append(event)
        # Include every association, even explicitly billed events, in ambiguity
        # detection. The same bytes on distinct URLs also count as reuse.
        by_hash = {}
        for url, associated in grouped.items():
            result = await self.fetch(url)
            if result:
                digest, data = result
                entry = by_hash.setdefault(digest, [data, []])
                entry[1].extend(associated)
        candidates = []
        for digest, (data, associated) in by_hash.items():
            identities = {(e.start, event_room(e), e.id) for e in associated}
            if len(identities) != 1:
                continue
            event = associated[0]
            description = ((event._raw_data or {}).get("fieldData") or {}).get("event-description", "")
            if _explicit_billed_names(description or ""):
                continue
            evidence = await self.read(digest, data)
            if evidence and evidence.matches(event):
                candidates.append((associated, evidence))
        names = list(dict.fromkeys(name for _, evidence in candidates for name in evidence.captions))
        if not names:
            return
        try:
            confirmed = await asyncio.to_thread(corroborate, names)
        except Exception as exc:
            Logger.warn(f"Gotham poster identity corroboration unavailable: {type(exc).__name__}")
            return
        recovered = 0
        for associated, evidence in candidates:
            names = tuple(dict.fromkeys(confirmed[name] for name in evidence.captions if name in confirmed))
            for event in associated:
                if names and evidence.matches(event):
                    event._poster_billing = (event.id, event.start, event.name, asset_url(event), names)
                    recovered += len(names)
        Logger.info(f"Gotham posters: checked {len(self.urls)} assets; recovered {recovered} corroborated performer memberships")
