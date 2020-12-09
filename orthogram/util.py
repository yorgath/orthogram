"""Utility functions."""

import sys

from typing import Any, Mapping

######################################################################

def log_warning(msg: str) -> None:
    """Print a warning message to standard error."""
    print("Warning: " + msg, file=sys.stderr)
