"""Utility functions."""

import sys

from typing import Any, Mapping

######################################################################

def log_debug(msg: str) -> None:
    """Print a debugging message to standard error."""
    print("Debug: " + msg, file=sys.stderr)

def log_info(msg: str) -> None:
    """Print an informational message to standard error."""
    print("Info: " + msg, file=sys.stderr)

def log_warning(msg: str) -> None:
    """Print a warning message to standard error."""
    print("Warning: " + msg, file=sys.stderr)
