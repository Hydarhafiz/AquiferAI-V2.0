"""
Test configuration and logging setup.

This module provides:
- Automatic logging to files in tests/logs/
- Tee output (both console and file)
- Timestamped log files for each test run
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from io import StringIO


class TeeOutput:
    """
    Tee output to both console and a file.

    This allows test output to be displayed in terminal AND saved to a log file.
    """

    def __init__(self, file_path: Path, original_stream):
        self.file = open(file_path, 'w', encoding='utf-8')
        self.original_stream = original_stream
        self.encoding = 'utf-8'

    def write(self, message):
        self.original_stream.write(message)
        self.file.write(message)
        self.file.flush()

    def flush(self):
        self.original_stream.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def setup_test_logging(test_name: str, phase: str = None) -> Path:
    """
    Set up logging for a test run.

    Creates a log file in tests/logs/<phase>/ with timestamp and test name.
    Redirects stdout/stderr to both console and file.

    Args:
        test_name: Name of the test (used in log filename)
        phase: Phase name (e.g., "phase1", "phase2"). If None, logs to root logs dir.

    Returns:
        Path to the log file
    """
    # Create logs directory (with optional phase subdirectory)
    tests_dir = Path(__file__).parent
    if phase:
        logs_dir = tests_dir / "logs" / phase
    else:
        logs_dir = tests_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{test_name}_{timestamp}.log"

    # Set up tee for stdout and stderr
    sys.stdout = TeeOutput(log_file, sys.__stdout__)
    sys.stderr = TeeOutput(log_file, sys.__stderr__)

    # Also configure Python logging to use the same file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.__stdout__)
        ],
        force=True
    )

    # Print header to log
    print(f"\n{'='*60}")
    print(f"TEST LOG: {test_name}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Log file: {log_file}")
    print(f"{'='*60}\n")

    return log_file


def teardown_test_logging(log_file: Path, passed: int, failed: int):
    """
    Clean up logging after test run.

    Args:
        log_file: Path to the log file
        passed: Number of tests passed
        failed: Number of tests failed
    """
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE")
    print(f"Finished: {datetime.now().isoformat()}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"Log saved to: {log_file}")
    print(f"{'='*60}\n")

    # Close tee streams
    if isinstance(sys.stdout, TeeOutput):
        sys.stdout.close()
        sys.stdout = sys.__stdout__
    if isinstance(sys.stderr, TeeOutput):
        sys.stderr.close()
        sys.stderr = sys.__stderr__


def get_latest_log(test_name: str = None) -> Path:
    """
    Get the most recent log file, optionally filtered by test name.

    Args:
        test_name: Optional filter for test name prefix

    Returns:
        Path to the most recent log file, or None if not found
    """
    logs_dir = Path(__file__).parent / "logs"
    if not logs_dir.exists():
        return None

    pattern = f"{test_name}_*.log" if test_name else "*.log"
    log_files = sorted(logs_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    return log_files[0] if log_files else None
