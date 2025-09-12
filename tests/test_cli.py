"""Tests for scrapeer_cli module."""

import json
import subprocess
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

import scrapeer_cli


class TestCliMain:
    """Tests for the CLI main function."""

    def test_main_with_valid_args_human_readable(self) -> None:
        """Test main function with valid arguments and human-readable output."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {
            "a1b2c3d4e5f6789012345678901234567890abcd": {
                "seeders": 10,
                "leechers": 5,
                "completed": 2
            }
        }
        mock_scraper.has_errors.return_value = False
        mock_scraper.get_errors.return_value = []

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                    output = mock_stdout.getvalue()
                    assert "Results:" in output
                    assert "a1b2c3d4e5f6789012345678901234567890abcd" in output
                    assert "Seeders: 10" in output
                    assert "Leechers: 5" in output
                    assert "Completed: 2" in output
                    assert "Summary: 1/1 infohashes found" in output

    def test_main_with_json_output(self) -> None:
        """Test main function with JSON output."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--json"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {
            "a1b2c3d4e5f6789012345678901234567890abcd": {
                "seeders": 10,
                "leechers": 5,
                "completed": 2
            }
        }
        mock_scraper.has_errors.return_value = False
        mock_scraper.get_errors.return_value = []

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                    output = mock_stdout.getvalue()
                    result = json.loads(output)
                    assert "results" in result
                    assert "errors" in result
                    assert "total_hashes" in result
                    assert "successful_hashes" in result
                    assert result["total_hashes"] == 1
                    assert result["successful_hashes"] == 1
                    hash_key = "a1b2c3d4e5f6789012345678901234567890abcd"
                    assert result["results"][hash_key]["seeders"] == 10

    def test_main_with_errors(self) -> None:
        """Test main function when scraper returns errors."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = True
        mock_scraper.get_errors.return_value = ["Connection timeout", "Invalid response"]

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 1  # Should exit with error code
                    output = mock_stdout.getvalue()
                    assert "No results found." in output
                    assert "Errors (2):" in output
                    assert "Connection timeout" in output
                    assert "Invalid response" in output

    def test_main_with_quiet_mode_errors(self) -> None:
        """Test main function with errors in quiet mode."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--quiet"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = True
        mock_scraper.get_errors.return_value = ["Connection timeout"]

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 1
                    output = mock_stdout.getvalue()
                    assert "No results found." in output
                    assert "Errors" not in output  # Should not show errors in quiet mode

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles keyboard interrupt."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = KeyboardInterrupt()

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 130  # Standard keyboard interrupt exit code
                    output = mock_stderr.getvalue()
                    assert "Operation cancelled by user." in output

    def test_main_keyboard_interrupt_quiet(self) -> None:
        """Test main function handles keyboard interrupt in quiet mode."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--quiet"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = KeyboardInterrupt()

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 130
                    output = mock_stderr.getvalue()
                    assert output == ""  # Should be silent in quiet mode

    def test_main_with_exception(self) -> None:
        """Test main function handles general exceptions."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = Exception("Test error")

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 1
                    output = mock_stderr.getvalue()
                    assert "Error: Test error" in output

    def test_main_with_exception_quiet(self) -> None:
        """Test main function handles exceptions in quiet mode."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--quiet"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.side_effect = Exception("Test error")

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        scrapeer_cli.main()

                    assert exc_info.value.code == 1
                    output = mock_stderr.getvalue()
                    assert output == ""  # Should be silent in quiet mode


class TestCliValidation:
    """Tests for CLI input validation."""

    def test_invalid_infohash_too_short(self) -> None:
        """Test validation of infohash that's too short."""
        test_args = [
            "scrapeer_cli.py",
            "abc123",  # Too short
            "-t", "udp://tracker.example.com:80",
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert "Invalid infohash 'abc123'" in output
                assert "Must be 40 hex characters" in output

    def test_invalid_infohash_too_long(self) -> None:
        """Test validation of infohash that's too long."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcdef",  # Too long (41 chars)
            "-t", "udp://tracker.example.com:80",
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert "Invalid infohash" in output

    def test_invalid_infohash_bad_characters(self) -> None:
        """Test validation of infohash with invalid characters."""
        test_args = [
            "scrapeer_cli.py",
            "g1h2i3j4k5l6789012345678901234567890abcd",  # Contains g,h,i,j,k,l
            "-t", "udp://tracker.example.com:80",
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert "Invalid infohash" in output

    def test_invalid_infohash_quiet_mode(self) -> None:
        """Test invalid infohash validation in quiet mode."""
        test_args = [
            "scrapeer_cli.py",
            "invalid",
            "-t", "udp://tracker.example.com:80",
            "--quiet"
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert output == ""  # Should be silent

    def test_timeout_too_low(self) -> None:
        """Test validation of timeout that's too low."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--timeout", "0"
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert "Timeout must be between 1 and 300 seconds" in output

    def test_timeout_too_high(self) -> None:
        """Test validation of timeout that's too high."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--timeout", "301"
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert "Timeout must be between 1 and 300 seconds" in output

    def test_timeout_validation_quiet_mode(self) -> None:
        """Test timeout validation in quiet mode."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--timeout", "0",
            "--quiet"
        ]

        with patch("sys.argv", test_args):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    scrapeer_cli.main()

                assert exc_info.value.code == 1
                output = mock_stderr.getvalue()
                assert output == ""  # Should be silent


class TestCliArguments:
    """Tests for CLI argument parsing."""

    def test_multiple_infohashes(self) -> None:
        """Test CLI with multiple infohashes."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "b2c3d4e5f6789012345678901234567890abcdef",
            "-t", "udp://tracker.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = False

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO):
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                # Verify scraper was called with correct arguments
                mock_scraper.scrape.assert_called_once()
                call_args = mock_scraper.scrape.call_args
                assert len(call_args.kwargs["hashes"]) == 2
                assert "a1b2c3d4e5f6789012345678901234567890abcd" in call_args.kwargs["hashes"]
                assert "b2c3d4e5f6789012345678901234567890abcdef" in call_args.kwargs["hashes"]

    def test_multiple_trackers(self) -> None:
        """Test CLI with multiple trackers."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker1.example.com:80", "udp://tracker2.example.com:80",
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = False

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO):
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                # Verify scraper was called with correct trackers
                call_args = mock_scraper.scrape.call_args
                assert len(call_args.kwargs["trackers"]) == 2
                assert "udp://tracker1.example.com:80" in call_args.kwargs["trackers"]
                assert "udp://tracker2.example.com:80" in call_args.kwargs["trackers"]

    def test_announce_mode(self) -> None:
        """Test CLI with announce mode enabled."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--announce"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = False

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO):
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                # Verify announce=True was passed
                call_args = mock_scraper.scrape.call_args
                assert call_args.kwargs["announce"] is True

    def test_max_trackers_option(self) -> None:
        """Test CLI with max trackers option."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--max-trackers", "5"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = False

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO):
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                # Verify max_trackers=5 was passed
                call_args = mock_scraper.scrape.call_args
                assert call_args.kwargs["max_trackers"] == 5

    def test_custom_timeout(self) -> None:
        """Test CLI with custom timeout."""
        test_args = [
            "scrapeer_cli.py",
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "-t", "udp://tracker.example.com:80",
            "--timeout", "10"
        ]

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {}
        mock_scraper.has_errors.return_value = False

        with patch("sys.argv", test_args):
            with patch("scrapeer_cli.Scraper", return_value=mock_scraper):
                with patch("sys.stdout", new_callable=StringIO):
                    scrapeer_cli.main()  # Should not raise SystemExit on success

                # Verify timeout=10 was passed
                call_args = mock_scraper.scrape.call_args
                assert call_args.kwargs["timeout"] == 10


class TestCliIntegration:
    """Integration tests for the CLI module."""

    @pytest.mark.timeout(10)
    def test_cli_help_option(self) -> None:
        """Test CLI help option works."""
        result = subprocess.run(
            [sys.executable, "scrapeer_cli.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        assert result.returncode == 0
        assert "Scrape BitTorrent trackers" in result.stdout
        assert "--trackers" in result.stdout
        assert "--timeout" in result.stdout
        assert "--announce" in result.stdout
        assert "--json" in result.stdout

    @pytest.mark.timeout(10)
    def test_cli_version_option(self) -> None:
        """Test CLI version option works."""
        result = subprocess.run(
            [sys.executable, "scrapeer_cli.py", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        assert result.returncode == 0
        assert "Scrapeer-py 1.0.3" in result.stdout

    @pytest.mark.timeout(10)
    def test_cli_missing_required_args(self) -> None:
        """Test CLI with missing required arguments."""
        result = subprocess.run(
            [sys.executable, "scrapeer_cli.py"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        assert result.returncode == 2  # argparse error code
        assert "the following arguments are required" in result.stderr

    @pytest.mark.timeout(10)
    def test_cli_missing_trackers(self) -> None:
        """Test CLI with missing trackers argument."""
        result = subprocess.run(
            [sys.executable, "scrapeer_cli.py", "a1b2c3d4e5f6789012345678901234567890abcd"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        assert result.returncode == 2
        assert "the following arguments are required: -t/--trackers" in result.stderr
