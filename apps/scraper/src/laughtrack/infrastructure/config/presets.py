from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig


class BatchConfigPresets:
    """Preset configurations for common venue types."""

    @staticmethod
    def get_comedy_venue_config() -> BatchScrapingConfig:
        """Standard configuration for comedy venues."""
        return BatchScrapingConfig(max_concurrent=5, delay_between_requests=0.5, batch_delay=1.0, enable_logging=True)

    @staticmethod
    def get_api_endpoint_config() -> BatchScrapingConfig:
        """Configuration optimized for API endpoints."""
        return BatchScrapingConfig(max_concurrent=3, delay_between_requests=0.3, batch_delay=0.5, enable_logging=True)

    @staticmethod
    def get_conservative_config() -> BatchScrapingConfig:
        """Conservative configuration for sensitive sites."""
        return BatchScrapingConfig(
            max_concurrent=2,
            delay_between_requests=1.0,
            batch_delay=2.0,
            batch_size=10,  # Process in small batches
            enable_logging=True,
        )

    @staticmethod
    def get_high_volume_config() -> BatchScrapingConfig:
        """Configuration for high-volume, fast APIs."""
        return BatchScrapingConfig(max_concurrent=10, delay_between_requests=0.1, batch_delay=0.2, enable_logging=True)


# Convenience functions for backward compatibility
def get_comedy_venue_config() -> BatchScrapingConfig:
    """Standard configuration for comedy venues."""
    return BatchConfigPresets.get_comedy_venue_config()


def get_api_endpoint_config() -> BatchScrapingConfig:
    """Configuration optimized for API endpoints."""
    return BatchConfigPresets.get_api_endpoint_config()


def get_conservative_config() -> BatchScrapingConfig:
    """Conservative configuration for sensitive sites."""
    return BatchConfigPresets.get_conservative_config()


def get_high_volume_config() -> BatchScrapingConfig:
    """Configuration for high-volume, fast APIs."""
    return BatchConfigPresets.get_high_volume_config()
