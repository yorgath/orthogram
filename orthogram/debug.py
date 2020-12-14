"""Debugging aids."""

class Debug:
    """Component of class that support debugging."""

    _debug = False

    @classmethod
    @property
    def debug(cls) -> bool:
        """Set this to enable debug messages."""
        return cls._debug

    @classmethod
    def set_debug(cls, value: bool) -> None:
        """Set the debug flag."""
        cls._debug = value
