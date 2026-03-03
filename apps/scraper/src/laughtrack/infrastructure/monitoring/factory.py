from typing import Optional

from laughtrack.core.services.monitoring import MonitoringService
from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig


class MonitoringFactory:
    """
    Factory for creating and configuring monitoring system components.

    This factory provides a simplified interface for creating monitoring components
    with proper configuration, reducing the complexity of manual setup.
    """

    @staticmethod
    def create_monitoring_service(config: Optional[MonitoringConfig] = None, logger=None) -> MonitoringService:
        """
        Create a complete MonitoringService with all components configured.

        Args:
            config: Monitoring configuration (uses defaults if None)
            logger: Logger instance

        Returns:
            Fully configured MonitoringService
        """
        monitoring_config = config or MonitoringConfig.default()

        # Validate configuration
        validation_issues = monitoring_config.validate()
        if validation_issues and logger:
            logger.log_warning(f"Monitoring configuration issues: {', '.join(validation_issues)}")

        # Create and return monitoring service (it self-configures based on config)
        return MonitoringService(config=monitoring_config)

    @staticmethod
    async def create_and_start_monitoring(config: Optional[MonitoringConfig] = None, logger=None) -> MonitoringService:
        """
        Create and start a complete monitoring service.

        Args:
            config: Monitoring configuration (uses defaults if None)
            logger: Logger instance

        Returns:
            Started MonitoringService
        """
        monitoring_config = config or MonitoringConfig.default()
        monitoring_service = MonitoringFactory.create_monitoring_service(config=monitoring_config, logger=logger)

        # Start background monitoring if enabled
        if monitoring_config.enable_background_monitoring and monitoring_service.alert_system:
            await monitoring_service.start_background_monitoring()
            if logger:
                logger.log_info("Background monitoring started")

        return monitoring_service

    @staticmethod
    def create_monitoring_components(config: Optional[MonitoringConfig] = None, logger=None) -> MonitoringService:
        """
        Create monitoring components for integration with existing systems.

        This is a convenience method for backward compatibility and integration
        with existing code that expects to get individual components.

        Args:
            config: Monitoring configuration (uses defaults if None)
            logger: Logger instance

        Returns:
            MonitoringService that provides access to all components
        """
        return MonitoringFactory.create_monitoring_service(config, logger)
