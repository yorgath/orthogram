"""Provides classes for naming drawing elements."""

from abc import ABCMeta

######################################################################

class Named(metaclass=ABCMeta):
    """Drawing element that has a name."""

    def __init__(self, name: str):
        """Initialize with the given name."""
        self._name = name

    def __repr__(self) -> str:
        """Convert to string."""
        cls = self.__class__.__name__
        name = self._name
        return f"{cls}({name})"

    @property
    def name(self) -> str:
        """Name of the element."""
        return self._name
