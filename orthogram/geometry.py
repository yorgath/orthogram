"""Points, lines etc."""

from abc import ABCMeta, abstractmethod
from enum import Enum, auto

from typing import Iterator, Tuple

######################################################################

class Orientation(Enum):
    """Orientation of a straight line or segment."""
    HORIZONTAL = auto()
    VERTICAL = auto()

class Direction(Enum):
    """Direction of a vector-like object."""
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()

######################################################################

class IntPoint:
    """Pair of integer coordinates."""

    def __init__(self, i: int, j: int):
        """Initialize point with vertical and horizontal coordinates."""
        self._i = int(i)
        self._j = int(j)

    @property
    def i(self) -> int:
        """Coordinate along the vertical axis."""
        return self._i

    @property
    def j(self) -> int:
        """Coordinate along the horizontal axis."""
        return self._j

    def __eq__(self, other: object) -> bool:
        """Implement the equality comparison between two points."""
        if not isinstance(other, IntPoint):
            return False
        return (self.i, self.j) == (other.i, other.j)

    def __hash__(self) -> int:
        """Return the hash value of the tuple of coordinates."""
        return hash((self.i, self.j))

    def __repr__(self) -> str:
        """Convert to string."""
        return "P(i={},j={})".format(self.i, self.j)

    def name(self) -> str:
        """Used as a key in graphs."""
        return repr(self)

######################################################################

class FloatPoint:
    """Pair of floating point coordinates."""

    def __init__(self, x: float, y: float):
        """Initialize point with horizontal and vertical coordinates."""
        self._x = float(x)
        self._y = float(y)

    @property
    def x(self) -> float:
        """Coordinate along the horizontal axis."""
        return self._x

    @property
    def y(self) -> float:
        """Coordinate along the vertical axis."""
        return self._y

    def __repr__(self) -> str:
        """Convert to string."""
        return "P(x={},y={})".format(self.x, self.y)

######################################################################

class OrientedObject(metaclass=ABCMeta):
    """An object that is either horizontal or vertical."""

    @property
    @abstractmethod
    def orientation(self) -> Orientation:
        """Orientation of the object."""

    def is_horizontal(self) -> bool:
        """True if the object is horizontal."""
        return self.orientation is Orientation.HORIZONTAL

    def is_vertical(self) -> bool:
        """True if the object is vertical."""
        return not self.is_horizontal()

######################################################################

class Axis(OrientedObject):
    """Grid axis, horizontal or vertical."""

    def __init__(self, orientation: Orientation, coord: int):
        """Initialize axis for the given orientation and coordinate."""
        self._orientation = orientation
        self._coordinate = coord

    @property
    def orientation(self) -> Orientation:
        """Orientation of the axis."""
        return self._orientation

    @property
    def coordinate(self) -> int:
        """Constant coordinate along the axis."""
        return self._coordinate

    def key(self) -> Tuple[Orientation, int]:
        """Used as an identifier for the axis."""
        return (self._orientation, self._coordinate)

    def __eq__(self, other: object) -> bool:
        """Implement the equality comparison between two axes."""
        if not isinstance(other, self.__class__):
            return False
        return self.key() == other.key()

    def __hash__(self) -> int:
        """Return the hash value of the key."""
        return hash(self.key())

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({}{})".format(
            self.__class__.__name__,
            self._orientation.name[0],
            self._coordinate
        )

######################################################################

class OrientedLine(OrientedObject, metaclass=ABCMeta):
    """Linear object that lies on a grid axis."""

    @property
    @abstractmethod
    def axis(self) -> Axis:
        """Axis on which the object lies."""

    @property
    def orientation(self) -> Orientation:
        """Orientation of the object."""
        return self.axis.orientation

######################################################################

class OrientedVector(OrientedLine, metaclass=ABCMeta):
    """Vector between two points, horizontal or vertical."""

    @property
    @abstractmethod
    def coordinates(self) -> Tuple[int, int]:
        """First and second coordinates along the axis."""

    @property
    def direction(self) -> Direction:
        """Direction of the object."""
        coords = self.coordinates
        if self.is_horizontal():
            if coords[0] < coords[1]:
                return Direction.RIGHT
            else:
                return Direction.LEFT
        else:
            if coords[0] < coords[1]:
                return Direction.DOWN
            else:
                return Direction.UP

    def point_at(self, coord: int) -> IntPoint:
        """Return the point on the axis at the given coordinate.

        It does not check whether the point lies inside the vector or
        not.

        """
        axis = self.axis
        if axis.is_horizontal():
            return IntPoint(axis.coordinate, coord)
        else:
            return IntPoint(coord, axis.coordinate)

    @property
    def first_point(self) -> IntPoint:
        """First point of the object."""
        coords = self.coordinates
        return self.point_at(coords[0])

    @property
    def last_point(self) -> IntPoint:
        """Last point of the object."""
        coords = self.coordinates
        return self.point_at(coords[1])

    def through_points(self) -> Iterator[IntPoint]:
        """Return an iterator over all the points along the axis."""
        c1, c2 = self.coordinates
        if c1 <= c2:
            r = range(c1, c2 + 1)
        else:
            r = range(c1, c2 - 1, -1)
        for c in r:
            yield self.point_at(c)
