"""Debugging aids."""

class Debug:
    """Component of class that support debugging."""

    _debug = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Return True if debugging is activated."""
        return cls._debug

    @classmethod
    def set_debug(cls, value: bool) -> None:
        """Set the debug flag."""
        cls._debug = value
