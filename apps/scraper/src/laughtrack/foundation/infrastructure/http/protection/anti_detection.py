"""
Enhanced anti-detection system for web scraping with human-like behavior patterns.

This module provides sophisticated anti-detection mechanisms including:
- Randomized delays with human-like patterns
- User agent rotation
- Session-aware request limiting
- Exponential backoff on errors
- Request pattern obfuscation
"""

import hashlib
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple
from urllib.parse import urlparse

from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class RequestSession:
    """Track request session state for anti-detection."""

    domain: str
    start_time: datetime
    request_count: int
    last_request: datetime
    consecutive_errors: int
    user_agent: str
    session_id: str


class AntiDetectionManager:
    """
    Advanced anti-detection manager with human-like behavior patterns.

    Features:
    - Randomized delays between requests (2-8 seconds base, with jitter)
    - User agent rotation per session
    - Session-based request limiting (max 50 requests per session)
    - Exponential backoff on errors
    - Time-of-day aware delays (slower during peak hours)
    - Request pattern obfuscation
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._sessions: Dict[str, RequestSession] = {}
        self._domain_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

        # Conservative rate limits for different domains
        self._domain_configs = {
            "www.tixr.com": {
                "min_delay": 3.0,  # Minimum 3 seconds between requests
                "max_delay": 8.0,  # Maximum 8 seconds between requests
                "session_limit": 30,  # Max 30 requests per session
                "session_duration": 1800,  # 30 minutes max session duration
                "error_backoff_base": 10.0,  # 10 second base backoff on errors
                "peak_hour_multiplier": 1.5,  # Slower during peak hours
            },
            "default": {
                "min_delay": 2.0,
                "max_delay": 5.0,
                "session_limit": 50,
                "session_duration": 3600,
                "error_backoff_base": 5.0,
                "peak_hour_multiplier": 1.2,
            },
        }

        # Realistic user agents (recent Chrome versions on different platforms)
        self._user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        ]

        self._initialized = True

    def _get_domain_lock(self, domain: str) -> threading.Lock:
        """Get or create a lock for the given domain."""
        if domain not in self._domain_locks:
            with self._global_lock:
                if domain not in self._domain_locks:
                    self._domain_locks[domain] = threading.Lock()
        return self._domain_locks[domain]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"

    def _get_config(self, domain: str) -> Dict:
        """Get configuration for a domain."""
        return self._domain_configs.get(domain, self._domain_configs["default"])

    def _generate_session_id(self, domain: str) -> str:
        """Generate a unique session ID."""
        timestamp = str(time.time())
        random_val = str(random.randint(10000, 99999))
        session_data = f"{domain}_{timestamp}_{random_val}"
        return hashlib.md5(session_data.encode()).hexdigest()[:12]

    def _get_or_create_session(self, domain: str) -> RequestSession:
        """Get existing session or create a new one."""
        now = datetime.now()
        config = self._get_config(domain)

        # Check if we have an active session
        if domain in self._sessions:
            session = self._sessions[domain]

            # Check if session should be renewed
            session_age = (now - session.start_time).total_seconds()
            should_renew = (
                session.request_count >= config["session_limit"]
                or session_age > config["session_duration"]
                or session.consecutive_errors >= 3
            )

            if not should_renew:
                return session

        # Create new session
        session = RequestSession(
            domain=domain,
            start_time=now,
            request_count=0,
            last_request=now - timedelta(seconds=config["max_delay"]),
            consecutive_errors=0,
            user_agent=random.choice(self._user_agents),
            session_id=self._generate_session_id(domain),
        )

        self._sessions[domain] = session
        return session

    def _calculate_delay(self, domain: str, session: RequestSession) -> float:
        """Calculate human-like delay between requests."""
        config = self._get_config(domain)

        # Base delay with randomization
        base_delay = random.uniform(config["min_delay"], config["max_delay"])

        # Add jitter to make it more human-like
        jitter = random.uniform(-0.5, 1.0)
        delay = base_delay + jitter

        # Peak hour adjustment (9 AM - 6 PM EST)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 18:
            delay *= config["peak_hour_multiplier"]

        # Error backoff
        if session.consecutive_errors > 0:
            backoff_multiplier = min(2**session.consecutive_errors, 8)  # Cap at 8x
            delay += config["error_backoff_base"] * backoff_multiplier

        # Progressive session delay (requests get slower as session progresses)
        session_progress = session.request_count / config["session_limit"]
        if session_progress > 0.7:  # After 70% of session limit
            delay *= 1.5

        return max(delay, 1.0)  # Minimum 1 second delay

    def _should_rotate_session(self, session: RequestSession) -> bool:
        """Determine if we should rotate to a new session."""
        config = self._get_config(session.domain)

        # Random rotation chance increases with session age and request count
        session_progress = session.request_count / config["session_limit"]
        rotation_chance = 0.05 + (session_progress * 0.15)  # 5-20% chance

        return random.random() < rotation_chance

    def wait_for_request(self, url: str, is_error: bool = False) -> Tuple[str, str]:
        """
        Wait appropriate time before making a request and return session info.

        Args:
            url: The URL being requested
            is_error: Whether the previous request resulted in an error

        Returns:
            Tuple of (user_agent, session_id) to use for the request
        """
        domain = self._extract_domain(url)
        domain_lock = self._get_domain_lock(domain)

        with domain_lock:
            session = self._get_or_create_session(domain)

            # Update error count
            if is_error:
                session.consecutive_errors += 1
            else:
                session.consecutive_errors = 0

            # Calculate delay
            delay = self._calculate_delay(domain, session)

            # Ensure minimum time since last request
            time_since_last = (datetime.now() - session.last_request).total_seconds()
            actual_delay = max(0, delay - time_since_last)

            if actual_delay > 0:
                time.sleep(actual_delay)

            # Update session state
            session.last_request = datetime.now()
            session.request_count += 1

            # Log the delay for monitoring
            Logger.debug(
                f"{domain}: Waiting {actual_delay:.2f}s "
                f"(session: {session.session_id}, requests: {session.request_count}, "
                f"errors: {session.consecutive_errors})"
            )

            return session.user_agent, session.session_id

    def get_session_stats(self) -> Dict[str, Dict]:
        """Get statistics about active sessions."""
        with self._global_lock:
            stats = {}
            for domain, session in self._sessions.items():
                config = self._get_config(domain)
                session_age = (datetime.now() - session.start_time).total_seconds()

                stats[domain] = {
                    "session_id": session.session_id,
                    "request_count": session.request_count,
                    "session_limit": config["session_limit"],
                    "session_age_minutes": round(session_age / 60, 1),
                    "consecutive_errors": session.consecutive_errors,
                    "user_agent": session.user_agent[:50] + "...",
                    "last_request": session.last_request.strftime("%H:%M:%S"),
                    "requests_remaining": config["session_limit"] - session.request_count,
                }
            return stats

    def force_session_rotation(self, domain: str) -> None:
        """Force creation of a new session for a domain."""
        domain_lock = self._get_domain_lock(domain)
        with domain_lock:
            if domain in self._sessions:
                old_session = self._sessions[domain]
                Logger.info(
                    f"Forcing session rotation for {domain} (old session: {old_session.session_id})"
                )
                del self._sessions[domain]

    def configure_domain(self, domain: str, **kwargs) -> None:
        """Configure anti-detection settings for a specific domain."""
        with self._global_lock:
            if domain not in self._domain_configs:
                self._domain_configs[domain] = self._domain_configs["default"].copy()

            self._domain_configs[domain].update(kwargs)
            Logger.debug(f"Updated config for {domain}: {kwargs}")


# Global anti-detection manager instance
anti_detection = AntiDetectionManager()

# Configure Tixr with very conservative settings
anti_detection.configure_domain(
    "www.tixr.com",
    min_delay=4.0,  # Minimum 4 seconds
    max_delay=12.0,  # Maximum 12 seconds
    session_limit=20,  # Only 20 requests per session
    session_duration=2400,  # 40 minutes max session
    error_backoff_base=15.0,  # 15 second base backoff
    peak_hour_multiplier=2.0,  # Much slower during peak hours
)
