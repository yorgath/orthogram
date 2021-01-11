"""Points, lines etc."""

from abc import ABCMeta, abstractmethod
from enum import Enum, auto

from typing import (
    Iterable,
    Iterator,
    Optional,
    Tuple,
)

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

    def __iter__(self) -> Iterator[int]:
        """Iterator over (i, j)."""
        yield self._i
        yield self._j

    def __repr__(self) -> str:
        """Convert to string."""
        return "P(i={},j={})".format(self.i, self.j)

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
        b = None
        for point in points:
            i, j = point
            if b:
                if i < b.imin:
                    b.imin = i
                if i > b.imax:
                    b.imax = i
                if j < b.jmin:
                    b.jmin = j
                if j > b.jmax:
                    b.jmax = j
            else:
                b = cls(imin=i, jmin=j, imax=i, jmax=j)
        return b

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

    @property
    def height(self) -> int:
        """Number of rows."""
        return self._imax - self._imin + 1

    @property
    def width(self) -> int:
        """Number of columns."""
        return self._jmax - self._jmin + 1

    @property
    def size(self) -> Tuple[int, int]:
        """Height and width of the bounding box."""
        return self.height, self.width

    def __iter__(self) -> Iterator[float]:
        """Return an iterator over the coordinates."""
        yield self._imin
        yield self._jmin
        yield self._imax
        yield self._jmax

    def copy(self) -> 'IntBounds':
        """Return a copy of the object."""
        return self.__class__(
            imin=self._imin,
            jmin=self._jmin,
            imax=self._imax,
            jmax=self._jmax,
        )

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

    def __iter__(self) -> Iterator[float]:
        """Return an iterator over the coordinates."""
        yield self._xmin
        yield self._ymin
        yield self._xmax
        yield self._ymax

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

    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self._xmax - self._xmin

    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self._ymax - self._ymin

    @property
    def size(self) -> Tuple[float, float]:
        """Width and height of the bounding box."""
        return self.width, self.height

    def expand(self, dx: float, dy: float) -> None:
        """Grow the box to a larger size."""
        self._xmax += dx
        self._ymax += dy

    def move(self, dx: float, dy: float) -> None:
        """Translate the origin of the box."""
        self._xmin += dx
        self._ymin += dy
        self._xmax += dx
        self._ymax += dy

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
        self._name = "{}{}".format(orientation.name[0], coord)

    @property
    def orientation(self) -> Orientation:
        """Orientation of the axis."""
        return self._orientation

    @property
    def coordinate(self) -> int:
        """Constant coordinate along the axis."""
        return self._coordinate

    @property
    def name(self) -> str:
        """Name of the axis (unique in the diagram)."""
        return self._name

    def __eq__(self, other: object) -> bool:
        """Implement the equality comparison between two axes."""
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """Return the hash value of the key."""
        return hash(self.name)

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({})".format(self.__class__.__name__, self.name)

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
