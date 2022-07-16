"""Points, lines etc."""

from dataclasses import dataclass
from enum import Enum, auto

from typing import (
    Iterable,
    Iterator,
    Optional,
    Tuple,
)

from .util import (
    class_str,
    vector_repr,
)

######################################################################

class Orientation(Enum):
    """Orientation of a straight line or segment."""
    HORIZONTAL = auto()
    VERTICAL = auto()

    def is_horizontal(self) -> bool:
        """True if the orientation is horizontal."""
        return self is Orientation.HORIZONTAL

    def is_vertical(self) -> bool:
        """True if the orientation is vertical."""
        return self is Orientation.VERTICAL

######################################################################

class Direction(Enum):
    """Direction of a vector-like object."""
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()

    def is_ascending(self) -> bool:
        """True if the direction goes from low coordinates to high ones."""
        return self in (Direction.DOWN, Direction.RIGHT)

    def is_descending(self) -> bool:
        """True if the direction goes from high coordinates to low ones."""
        return not self.is_ascending()

######################################################################

@dataclass(frozen=True)
class IntPoint:
    """Pair of integer coordinates."""
    i: int
    j: int

######################################################################

@dataclass
class IntBounds:
    """Bounding box on a grid.

    This is a mutable object, so you are advised to make a copy if you
    want to give it away but do not want it to be mutated.

    """
    imin: int
    jmin: int
    imax: int
    jmax: int

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

    def copy(self) -> 'IntBounds':
        """Return a copy of the object."""
        return self.__class__(
            imin=self.imin,
            jmin=self.jmin,
            imax=self.imax,
            jmax=self.jmax,
        )

    def expand_to(self, point: IntPoint) -> None:
        """Expand the box to include the given point."""
        i = point.i
        if i < self.imin:
            self.imin = i
        if i > self.imax:
            self.imax = i
        j = point.j
        if j < self.jmin:
            self.jmin = j
        if j > self.jmax:
            self.jmax = j

    def on_perimeter(self, point: IntPoint) -> bool:
        """Answer whether the point is on the perimeter of the box."""
        i, j = point.i, point.j
        return (
            i == self.imin or i == self.imax or
            j == self.jmin or j == self.jmax
        )

######################################################################

@dataclass(frozen=True)
class FloatPoint:
    """Pair of floating point coordinates."""
    x: float
    y: float

######################################################################

@dataclass(frozen=True)
class Axis:
    """Grid axis, horizontal or vertical."""
    orientation: Orientation
    coordinate: int

    def __repr__(self) -> str:
        """Represent as string."""
        return class_str(self, self.name)

    def is_horizontal(self) -> bool:
        """True if the axis is horizontal."""
        return self.orientation.is_horizontal()

    def point_at(self, coord: int) -> IntPoint:
        """Return the point on the axis at the given coordinate."""
        if self.is_horizontal():
            return IntPoint(self.coordinate, coord)
        return IntPoint(coord, self.coordinate)

    @property
    def name(self) -> str:
        """Name of the axis."""
        ori = self.orientation.name[0]
        coord = self.coordinate
        return f"{ori}{coord}"

######################################################################

class OrientedVector:
    """Vector between two points, horizontal or vertical."""

    def __init__(
            self,
            axis: Axis,
            coordinates: Tuple[int, int],
    ):
        """Initialize given the axis and the pair of coordinates."""
        self._axis = axis
        self._coords = coordinates

    def __repr__(self) -> str:
        """Represent as string."""
        axis = repr(self._axis.name)
        vec = vector_repr(*self._coords)
        content = f"axis={axis}, coords={vec}"
        return class_str(self, content)

    @property
    def axis(self) -> Axis:
        """Axis on which the vector lies."""
        return self._axis

    @property
    def orientation(self) -> Orientation:
        """Orientation of the vector."""
        return self.axis.orientation

    def is_horizontal(self) -> bool:
        """True if the vector is horizontal."""
        return self.axis.is_horizontal()

    def is_vertical(self) -> bool:
        """True if the vector is vertical."""
        return not self.is_horizontal()

    @property
    def coordinates(self) -> Tuple[int, int]:
        """First and second coordinates along the axis."""
        return self._coords

    @property
    def min_max_coordinates(self) -> Tuple[int, int]:
        """Coordinates in increasing order."""
        return self.min_coord, self.max_coord

    @property
    def min_coord(self) -> int:
        """Minimum coordinate along the axis."""
        return min(self._coords)

    @property
    def max_coord(self) -> int:
        """Maximum coordinate along the axis."""
        return max(self._coords)

    @property
    def length(self) -> int:
        """Length of the vector."""
        coords = self._coords
        return abs(coords[1] - coords[0])

    @property
    def direction(self) -> Direction:
        """Direction of the vector."""
        coords = self.coordinates
        if self.is_horizontal():
            if coords[0] < coords[1]:
                return Direction.RIGHT
            return Direction.LEFT
        if coords[0] < coords[1]:
            return Direction.DOWN
        return Direction.UP

    @property
    def points(self) -> Tuple[IntPoint, IntPoint]:
        """First and last points of the vector."""
        return self.first_point, self.last_point

    @property
    def first_point(self) -> IntPoint:
        """First point of the vector."""
        coords = self.coordinates
        return self.axis.point_at(coords[0])

    @property
    def last_point(self) -> IntPoint:
        """Last point of the vector."""
        coords = self.coordinates
        return self.axis.point_at(coords[1])

    def through_points(self) -> Iterator[IntPoint]:
        """Iterate over all the points along the axis."""
        coord_1, coord_2 = self.coordinates
        if coord_1 <= coord_2:
            span = range(coord_1, coord_2 + 1)
        else:
            span = range(coord_1, coord_2 - 1, -1)
        for coord in span:
            yield self.axis.point_at(coord)

    def vector_depiction(self) -> str:
        """Return a string depicting the vector."""
        axis = self.axis.name
        vec = vector_repr(*self.coordinates)
        return f"{axis}{vec}"
