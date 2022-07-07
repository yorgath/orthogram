"""Utility functions."""

from sys import stderr

######################################################################

def class_str(obj: object, content: object) -> str:
    """Helper for representation methods."""
    cls = obj.__class__.__name__
    return f"{cls}({content})"

def grid_str(height: int, width: int) -> str:
    """Return a string that shows the dimensions of a grid."""
    return f"rows={height}, columns={width}"

def vector_repr(start: object, end: object) -> str:
    """Return a string depicting a vector from start to end."""
    return f"[{repr(start)} -> {repr(end)}]"

def indent(level: int) -> str:
    """Return a string which is useful for indenting lines."""
    return 4 * level * " "

######################################################################

def log_debug(msg: str) -> None:
    """Print a debugging message to standard error."""
    print("Debug: " + msg, file=stderr)

def log_info(msg: str) -> None:
    """Print an informational message to standard error."""
    print("Info: " + msg, file=stderr)

def log_warning(msg: str) -> None:
    """Print a warning message to standard error."""
    print("Warning: " + msg, file=stderr)
