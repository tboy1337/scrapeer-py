"""
Production-ready configuration for Scrapeer.
"""

import copy
import logging
import os
from typing import Dict, Union, Optional, cast

# Type aliases
LoggingConfigDict = Dict[str, Union[str, int, None]]
ScraperConfigDict = Dict[str, Union[str, int]]
NetworkConfigDict = Dict[str, int]
ConfigValue = Union[str, int, None, LoggingConfigDict, ScraperConfigDict, NetworkConfigDict]
ConfigDict = Dict[str, ConfigValue]

# Default configuration components
_DEFAULT_LOGGING_CONFIG: LoggingConfigDict = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": None,  # Set to a file path to log to file
}

_DEFAULT_SCRAPER_CONFIG: ScraperConfigDict = {
    "default_timeout": 2,
    "max_retries": 3,
    "max_trackers_per_request": 10,
    "user_agent": "Scrapeer-py/1.0.0",
}

_DEFAULT_NETWORK_CONFIG: NetworkConfigDict = {
    "connection_pool_size": 10,
    "max_concurrent_requests": 5,
}

# Default configuration
DEFAULT_CONFIG: ConfigDict = {
    "logging": _DEFAULT_LOGGING_CONFIG,
    "scraper": _DEFAULT_SCRAPER_CONFIG,
    "network": _DEFAULT_NETWORK_CONFIG,
}


def configure_logging(config: Optional[LoggingConfigDict] = None) -> None:
    """
    Configure logging for the entire application.

    Args:
        config: Logging configuration dictionary
    """
    if config is None:
        config = cast(LoggingConfigDict, DEFAULT_CONFIG["logging"])

    try:
        level_str = config.get("level", "INFO")
        level_str = level_str if isinstance(level_str, str) else "INFO"
        level = getattr(logging, level_str.upper())  # type: ignore[misc]
    except AttributeError:
        level = logging.INFO

    log_format = config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_format = log_format if isinstance(log_format, str) else (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = config.get("file")
    log_file = log_file if isinstance(log_file, str) else None

    # Configure root logger for scrapeer
    logger = logging.getLogger("scrapeer")
    logger.setLevel(level)  # type: ignore[misc]

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            logger.warning("Could not create log file %s: %s", log_file, e)


def get_config() -> ConfigDict:
    """
    Get application configuration with environment variable overrides.

    Returns:
        Complete configuration dictionary
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    # Override with environment variables
    log_level = os.getenv("SCRAPEER_LOG_LEVEL")
    if log_level:
        logging_config = config.get("logging")
        if isinstance(logging_config, dict):
            logging_config = cast(LoggingConfigDict, logging_config)
            logging_config["level"] = log_level

    log_file = os.getenv("SCRAPEER_LOG_FILE")
    if log_file:
        logging_config = config.get("logging")
        if isinstance(logging_config, dict):
            logging_config = cast(LoggingConfigDict, logging_config)
            logging_config["file"] = log_file

    timeout_env = os.getenv("SCRAPEER_TIMEOUT")
    if timeout_env:
        try:
            timeout_val = int(timeout_env)
            scraper_config = config.get("scraper")
            if isinstance(scraper_config, dict):
                scraper_config["default_timeout"] = timeout_val
        except ValueError:
            pass

    return config


# Initialize logging with default configuration
configure_logging()
