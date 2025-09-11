"""Tests for scrapeer.config module."""

import logging
import os
import tempfile
from unittest.mock import patch


from scrapeer.config import (
    DEFAULT_CONFIG,
    configure_logging,
    get_config,
)


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_config_structure(self) -> None:
        """Test that default config has expected structure."""
        assert "logging" in DEFAULT_CONFIG
        assert "scraper" in DEFAULT_CONFIG
        assert "network" in DEFAULT_CONFIG

        # Check logging config
        logging_config = DEFAULT_CONFIG["logging"]
        assert "level" in logging_config
        assert "format" in logging_config
        assert "file" in logging_config
        assert logging_config["level"] == "INFO"
        assert logging_config["file"] is None

        # Check scraper config
        scraper_config = DEFAULT_CONFIG["scraper"]
        assert "default_timeout" in scraper_config
        assert "max_retries" in scraper_config
        assert "max_trackers_per_request" in scraper_config
        assert "user_agent" in scraper_config
        assert scraper_config["default_timeout"] == 2
        assert scraper_config["user_agent"] == "Scrapeer-py/1.0.0"

        # Check network config
        network_config = DEFAULT_CONFIG["network"]
        assert "connection_pool_size" in network_config
        assert "max_concurrent_requests" in network_config


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_with_default_config(self) -> None:
        """Test logging configuration with default settings."""
        configure_logging()

        logger = logging.getLogger("scrapeer")
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_configure_logging_with_custom_config(self) -> None:
        """Test logging configuration with custom settings."""
        config = {
            "level": "DEBUG",
            "format": "%(levelname)s - %(message)s",
        }

        configure_logging(config)

        logger = logging.getLogger("scrapeer")
        assert logger.level == logging.DEBUG

    def test_configure_logging_with_invalid_level(self) -> None:
        """Test logging configuration with invalid log level."""
        config = {
            "level": "INVALID_LEVEL",
        }

        # Should not raise exception, falls back to INFO
        configure_logging(config)

        logger = logging.getLogger("scrapeer")
        # Should fall back to INFO level
        assert logger.level == logging.INFO

    def test_configure_logging_with_file_handler(self) -> None:
        """Test logging configuration with file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_filename = os.path.join(temp_dir, "test.log")

            config = {
                "level": "INFO",
                "format": "%(levelname)s - %(message)s",
                "file": temp_filename,
            }

            configure_logging(config)

            logger = logging.getLogger("scrapeer")

            # Should have both console and file handlers
            assert len(logger.handlers) >= 2

            # Check that one handler is a FileHandler
            file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
            assert len(file_handlers) > 0

            # Close file handlers to release file locks
            for handler in file_handlers:
                handler.close()
                logger.removeHandler(handler)

    def test_configure_logging_with_invalid_file_path(self) -> None:
        """Test logging configuration with invalid file path."""
        config = {
            "level": "INFO",
            "format": "%(levelname)s - %(message)s",
            "file": "/invalid/path/that/does/not/exist/test.log",
        }

        # Should not raise exception, just skip file handler
        configure_logging(config)

        logger = logging.getLogger("scrapeer")
        assert len(logger.handlers) > 0

    def test_configure_logging_removes_existing_handlers(self) -> None:
        """Test that configure_logging removes existing handlers."""
        logger = logging.getLogger("scrapeer")

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)
        _ = len(logger.handlers)

        configure_logging()

        # Should have replaced existing handlers
        final_handlers = logger.handlers
        assert dummy_handler not in final_handlers


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_default(self) -> None:
        """Test getting default configuration."""
        config = get_config()

        assert config == DEFAULT_CONFIG
        # Ensure it's a copy, not the original
        assert config is not DEFAULT_CONFIG

    @patch.dict(os.environ, {
        "SCRAPEER_LOG_LEVEL": "DEBUG",
        "SCRAPEER_LOG_FILE": "/tmp/test.log",
        "SCRAPEER_TIMEOUT": "10"
    })
    def test_get_config_with_env_overrides(self) -> None:
        """Test configuration with environment variable overrides."""
        config = get_config()

        assert config["logging"]["level"] == "DEBUG"
        assert config["logging"]["file"] == "/tmp/test.log"
        assert config["scraper"]["default_timeout"] == 10

    @patch.dict(os.environ, {"SCRAPEER_TIMEOUT": "invalid_number"})
    def test_get_config_with_invalid_timeout_env(self) -> None:
        """Test configuration with invalid timeout environment variable."""
        config = get_config()

        # Should fall back to default timeout
        assert config["scraper"]["default_timeout"] == DEFAULT_CONFIG["scraper"]["default_timeout"]

    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_with_no_env_vars(self) -> None:
        """Test configuration with no environment variables set."""
        config = get_config()

        # Should return default config
        assert config["logging"]["level"] == DEFAULT_CONFIG["logging"]["level"]
        assert config["logging"]["file"] == DEFAULT_CONFIG["logging"]["file"]
        assert config["scraper"]["default_timeout"] == DEFAULT_CONFIG["scraper"]["default_timeout"]

    def test_get_config_partial_env_overrides(self) -> None:
        """Test configuration with partial environment overrides."""
        with patch.dict(os.environ, {"SCRAPEER_LOG_LEVEL": "ERROR"}, clear=False):
            config = get_config()

            # Only log level should be overridden
            assert config["logging"]["level"] == "ERROR"
            assert config["logging"]["file"] == DEFAULT_CONFIG["logging"]["file"]
            assert (
                config["scraper"]["default_timeout"] ==
                DEFAULT_CONFIG["scraper"]["default_timeout"]
            )

    def test_get_config_returns_copy(self) -> None:
        """Test that get_config returns a copy, not reference to DEFAULT_CONFIG."""
        config1 = get_config()
        config2 = get_config()

        # Both should be equal but not the same object
        assert config1 == config2
        assert config1 is not config2
        assert config1 is not DEFAULT_CONFIG


class TestConfigEnvironmentOverrides:
    """Tests for environment variable overrides in configuration."""

    @patch.dict(os.environ, {"SCRAPEER_LOG_LEVEL": "DEBUG"})
    def test_env_log_level_override(self) -> None:
        """Test that environment variable overrides log level."""
        config = get_config()

        assert config["logging"]["level"] == "DEBUG"

    @patch.dict(os.environ, {"SCRAPEER_LOG_FILE": "/tmp/test.log"})
    def test_env_log_file_override(self) -> None:
        """Test that environment variable overrides log file."""
        config = get_config()

        assert config["logging"]["file"] == "/tmp/test.log"

    @patch.dict(os.environ, {"SCRAPEER_TIMEOUT": "60"})
    def test_env_timeout_override(self) -> None:
        """Test that environment variable overrides timeout."""
        config = get_config()

        assert config["scraper"]["default_timeout"] == 60

    @patch.dict(os.environ, {"SCRAPEER_TIMEOUT": "invalid"}, clear=True)
    def test_env_timeout_invalid_value(self) -> None:
        """Test that invalid timeout environment variable is ignored."""
        config = get_config()

        # Should keep default timeout value
        assert config["scraper"]["default_timeout"] == 2
