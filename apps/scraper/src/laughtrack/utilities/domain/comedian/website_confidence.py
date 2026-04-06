"""
Scores how likely a URL is to be a comedian's actual personal/official website.

Returns a confidence level (high/medium/low) and the numeric score.

Heuristics:
  +3  comedian's name appears in the domain
  +1  URL is root-level (not a deep path)
  +1  JSON-LD events were found on the site (caller adds this)
  -3  domain is a known aggregator / venue / agency site
  -4  domain is a social media platform
  -1  free website builder subdomain (wixsite, weebly, etc.)
  -2  deep subdirectory path (2+ segments)
  -1  name not in domain (and not a builder subdomain)
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


# ------------------------------------------------------------------ #
# Domain lists                                                        #
# ------------------------------------------------------------------ #

AGGREGATOR_DOMAINS = frozenset({
    # Comedy club / venue sites
    "westsidecomedyclub.com", "arubacomedy.com", "greenwichvillagecomedyclub.com",
    "ucbcomedy.com", "grislypearstandup.com", "lafayettecomedy.com",
    "eastvillecomedy.com", "empirecomedyme.com", "blcomedy.com",
    "comedycraftbeer.com", "acmecomedycompany.com", "quezadas.com",
    "spotlight29.com", "thetopsecretcomedyclub.co.uk", "improvla.com",
    "laughfactory.com", "comedycellar.com", "heliumcomedy.com",
    "zanies.com", "funnybone.com", "improv.com", "standuplive.com",
    # Directories / aggregators
    "comedy.co.uk", "thebash.com", "thecomedybureau.com", "acjokes.com",
    "voyagela.com", "justdial.com", "theimaginaryagency.com",
    # Talent agencies
    "unitedtalent.com", "avalonuk.com", "offthekerb.com",
    "pfrtalent.com", "gershtla.com", "comedydynamics.com",
    # Generic platforms used as "website"
    "linktr.ee", "beacons.ai", "allmylinks.com", "campsite.bio",
    "bio.site", "solo.to", "hoo.be", "stan.store",
})

SOCIAL_DOMAINS = frozenset({
    "instagram.com", "twitter.com", "x.com", "facebook.com",
    "tiktok.com", "youtube.com", "twitch.tv", "threads.net",
    "snapchat.com",
})

_BUILDER_SUBDOMAIN_PATTERNS = [
    re.compile(r"\.wixsite\.com$", re.IGNORECASE),
    re.compile(r"\.weebly\.com$", re.IGNORECASE),
    re.compile(r"\.squarespace\.com$", re.IGNORECASE),
    re.compile(r"\.wordpress\.com$", re.IGNORECASE),
    re.compile(r"\.blogspot\.com$", re.IGNORECASE),
    re.compile(r"\.carrd\.co$", re.IGNORECASE),
    re.compile(r"\.godaddysites\.com$", re.IGNORECASE),
    re.compile(r"\.webflow\.io$", re.IGNORECASE),
]


# ------------------------------------------------------------------ #
# Scoring                                                             #
# ------------------------------------------------------------------ #

@dataclass
class WebsiteScore:
    points: int = 0
    signals: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> str:
        if self.points >= 3:
            return "high"
        elif self.points >= 1:
            return "medium"
        else:
            return "low"


def _normalize_name(name: str) -> list[str]:
    """Extract meaningful name parts (4+ chars) for domain matching."""
    cleaned = re.sub(r'[""\'()\[\]]', '', name)
    parts = re.sub(r'[^a-z\s]', '', cleaned.lower()).split()
    return [p for p in parts if len(p) >= 4]


def score_website(name: str, url: str, has_events: bool = False) -> WebsiteScore:
    """Score a comedian website URL for confidence.

    Args:
        name: comedian name
        url: website URL
        has_events: whether JSON-LD events were found on the site
    """
    result = WebsiteScore()

    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    name_parts = _normalize_name(name)

    # --- Positive signals --- #

    if name_parts and any(part in domain.replace("-", "").replace(".", "") for part in name_parts):
        result.points += 3
        result.signals.append("name_in_domain")

    path_segments = [s for s in parsed.path.rstrip("/").split("/") if s]
    if len(path_segments) <= 1:
        result.points += 1
        result.signals.append("root_url")

    if has_events:
        result.points += 1
        result.signals.append("has_events")

    # --- Negative signals --- #

    if domain in AGGREGATOR_DOMAINS or any(domain.endswith("." + d) for d in AGGREGATOR_DOMAINS):
        result.points -= 3
        result.signals.append("aggregator_domain")

    if domain in SOCIAL_DOMAINS or any(domain.endswith("." + d) for d in SOCIAL_DOMAINS):
        result.points -= 4
        result.signals.append("social_media")

    is_builder = False
    for pattern in _BUILDER_SUBDOMAIN_PATTERNS:
        if pattern.search(parsed.netloc):
            result.points -= 1
            result.signals.append("builder_subdomain")
            is_builder = True
            break

    if len(path_segments) >= 2:
        result.points -= 2
        result.signals.append("deep_path")

    if name_parts and not any(part in domain.replace("-", "").replace(".", "") for part in name_parts):
        if not is_builder:
            result.points -= 1
            result.signals.append("name_not_in_domain")

    return result
