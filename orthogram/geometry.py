"""Points, lines etc."""

from abc import ABCMeta, abstractmethod
from enum import Enum, auto

from typing import (
    Iterable,
    Iterator,
    Optional,
    Tuple,
)

from .names import Named

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

    def __eq__(self, other: object) -> bool:
        """Implement the equality comparison between two points."""
        if not isinstance(other, IntPoint):
            return False
        return (self.i, self.j) == (other.i, other.j)

    def __hash__(self) -> int:
        """Return the hash value of the tuple of coordinates."""
        return hash((self._i, self._j))

    def __repr__(self) -> str:
        """Convert to string."""
        return "P(i={},j={})".format(self._i, self._j)

    @property
    def i(self) -> int:
        """Coordinate along the vertical axis."""
        return self._i

    @property
    def j(self) -> int:
        """Coordinate along the horizontal axis."""
        return self._j

######################################################################

class IntBounds:
    """Bounding box on a grid.

    This is a mutable object, so you are advised to make a copy if you
    want to give it away but do not want it to be mutated.

    """

    def __init__(self, imin: int, jmin: int, imax: int, jmax: int) -> None:
        """Initialize the bounds with the given coordinates."""
        self._imin = imin
        self._jmin = jmin
        self._imax = imax
        self._jmax = jmax

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}(imin={},jmin={},imax={},jmax={})".format(
            self.__class__.__name__,
            self._imin, self._jmin, self._imax, self._jmax,
        )

    @classmethod
    def containing(cls, points: Iterable[IntPoint]) -> Optional['IntBounds']:
        """Create a bounding box that contains all the points.

        It returns None if the collection of points is empty.

        """
        bounds = None
        for point in points:
            i, j = point.i, point.j
            if bounds:
                if i < bounds.imin:
                    bounds.imin = i
                if i > bounds.imax:
                    bounds.imax = i
                if j < bounds.jmin:
                    bounds.jmin = j
                if j > bounds.jmax:
                    bounds.jmax = j
            else:
                bounds = cls(imin=i, jmin=j, imax=i, jmax=j)
        return bounds

    @property
    def imin(self) -> int:
        """Index of first row."""
        return self._imin

    @imin.setter
    def imin(self, value: int) -> None:
        self._imin = value

    @property
    def jmin(self) -> int:
        """Index of first column."""
        return self._jmin

    @jmin.setter
    def jmin(self, value: int) -> None:
        self._jmin = value

    @property
    def imax(self) -> int:
        """Index of last row."""
        return self._imax

    @imax.setter
    def imax(self, value: int) -> None:
        self._imax = value

    @property
    def jmax(self) -> int:
        """Index of last column."""
        return self._jmax

    @jmax.setter
    def jmax(self, value: int) -> None:
        self._jmax = value

    def copy(self) -> 'IntBounds':
        """Return a copy of the object."""
        return self.__class__(
            imin=self._imin,
            jmin=self._jmin,
            imax=self._imax,
            jmax=self._jmax,
        )

    def expand_to(self, point: IntPoint) -> None:
        """Expand the box to include the given point."""
        i = point.i
        if i < self._imin:
            self._imin = i
        if i > self._imax:
            self._imax = i
        j = point.j
        if j < self._jmin:
            self._jmin = j
        if j > self._jmax:
            self._jmax = j

######################################################################

class FloatPoint:
    """Pair of floating point coordinates."""

    def __init__(self, x: float, y: float):
        """Initialize point with horizontal and vertical coordinates."""
        self._x = float(x)
        self._y = float(y)

    def __repr__(self) -> str:
        """Convert to string."""
        return "P(x={},y={})".format(self._x, self._y)

    @property
    def x(self) -> float:
        """Coordinate along the horizontal axis."""
        return self._x

    @property
    def y(self) -> float:
        """Coordinate along the vertical axis."""
        return self._y

######################################################################

class FloatBounds:
    """Bounding box with floating point coordinates."""

    def __init__(
            self,
            xmin: float, ymin: float,
            xmax: float, ymax: float
    ) -> None:
        """Initialize the bounds with the given coordinates."""
        self._xmin = xmin
        self._ymin = ymin
        self._xmax = xmax
        self._ymax = ymax

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}(xmin={},ymin={},xmax={},ymax={})".format(
            self.__class__.__name__,
            self._xmin, self._ymin, self._xmax, self._ymax,
        )

    @property
    def xmin(self) -> float:
        """Leftmost coordinate."""
        return self._xmin

    @property
    def ymin(self) -> float:
        """Topmost coordinate."""
        return self._ymin

    @property
    def xmax(self) -> float:
        """Rightmost coordinate."""
        return self._xmax

    @property
    def ymax(self) -> float:
        """Bottommost coordinate."""
        return self._ymax

######################################################################

class OrientedObject(metaclass=ABCMeta):
    """An object that is either horizontal or vertical."""

    def is_horizontal(self) -> bool:
        """True if the object is horizontal."""
        return self.orientation is Orientation.HORIZONTAL

    def is_vertical(self) -> bool:
        """True if the object is vertical."""
        return not self.is_horizontal()

    @property
    @abstractmethod
    def orientation(self) -> Orientation:
        """Orientation of the object."""

######################################################################

class Axis(Named, OrientedObject):
    """Grid axis, horizontal or vertical."""

    def __init__(self, orientation: Orientation, coord: int):
        """Initialize axis for the given orientation and coordinate."""
        name = f"{orientation.name[0]}{coord}"
        super().__init__(name)
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

    def __eq__(self, other: object) -> bool:
        """Implement the equality comparison between two axes."""
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """Return the hash value of the unique name."""
        return hash(self._name)

######################################################################

class OrientedLine(OrientedObject, metaclass=ABCMeta):
    """Linear object that lies on a grid axis."""

    @property
    def orientation(self) -> Orientation:
        """Orientation of the object."""
        return self.axis.orientation

    @property
    @abstractmethod
    def axis(self) -> Axis:
        """Axis on which the object lies."""

######################################################################

class OrientedVector(OrientedLine, metaclass=ABCMeta):
    """Vector between two points, horizontal or vertical."""

    @property
    def direction(self) -> Direction:
        """Direction of the object."""
        coords = self.coordinates
        if self.is_horizontal():
            if coords[0] < coords[1]:
                return Direction.RIGHT
            return Direction.LEFT
        if coords[0] < coords[1]:
            return Direction.DOWN
        return Direction.UP

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

    def point_at(self, coord: int) -> IntPoint:
        """Return the point on the axis at the given coordinate.

        It does not check whether the point lies inside the vector or
        not.

        """
        axis = self.axis
        if axis.is_horizontal():
            return IntPoint(axis.coordinate, coord)
        return IntPoint(coord, axis.coordinate)

    def through_points(self) -> Iterator[IntPoint]:
        """Return an iterator over all the points along the axis."""
        coord_1, coord_2 = self.coordinates
        if coord_1 <= coord_2:
            span = range(coord_1, coord_2 + 1)
        else:
            span = range(coord_1, coord_2 - 1, -1)
        for coord in span:
            yield self.point_at(coord)

    @property
    @abstractmethod
    def coordinates(self) -> Tuple[int, int]:
        """First and second coordinates along the axis."""

    @property
    def min_max_coordinates(self) -> Tuple[int, int]:
        """Coordinates in increasing order."""
        first, second = self.coordinates
        if first > second:
            return second, first
        return first, second
