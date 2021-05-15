"""Provides classes for drawing shapes."""

from typing import Optional

from shapely import affinity # type: ignore

from shapely.geometry import ( # type: ignore
    LinearRing,
    LineString,
    Point,
    Polygon,
)

from ..arrange import Wire
from ..define import ConnectionAttributes
from ..util import log_warning

from .functions import buffer_rectangle

######################################################################

class Arrow:
    """Represents an arrow at the end of a connection line."""

    def __init__(self, attrs: ConnectionAttributes):
        """Initialize for the given attributes."""
        self._aspect = aspect = attrs.arrow_aspect
        width = attrs.stroke_width * attrs.arrow_base
        self._length = width * aspect
        self._geometry: Optional[LinearRing] = None

    @property
    def length(self) -> float:
        """Length of the arrow from base to tip."""
        return self._length

    def is_valid(self) -> bool:
        """True if the arrow has its geometry set."""
        return self._geometry is not None

    @property
    def geometry(self) -> Optional[LinearRing]:
        """Geometry used to draw the arrow."""
        return self._geometry

    def set_geometry(self, base_middle: Point, tip: Point) -> None:
        """Calculate the geometry of the arrow using the points."""
        coords = [tip]
        ls1 = LineString((base_middle, tip))
        fact = 0.5 / self._aspect
        ls2 = affinity.scale(ls1, fact, fact, 1.0, base_middle)
        ls3 = affinity.rotate(ls2, -90, base_middle)
        coords.append(ls3.coords[-1])
        ls4 = affinity.rotate(ls2, 90, base_middle)
        coords.append(ls4.coords[-1])
        self._geometry = LinearRing(coords)

######################################################################

class WireLine:
    """Encapsulates the geometry for a connection wire."""

    def __init__(
            self,
            wire: Wire,
            start_polygon: Polygon,
            end_polygon: Polygon,
            line_string: LineString,
    ):
        """Initialize for the given wire.

        The polygons will be used to clip the line to its proper
        dimensions.

        """
        self._wire = wire
        self._start_polygon = start_polygon
        self._end_polygon = end_polygon
        self._wire_line_string = line_string
        self._start_arrow: Optional[Arrow] = None
        self._clip_start()
        self._end_arrow: Optional[Arrow] = None
        self._clip_end()

    @property
    def connection_attributes(self) -> ConnectionAttributes:
        """Attributes of the underlying diagram connection."""
        return self._wire.connection.attributes

    @property
    def wire_line_string(self) -> LineString:
        """The line string to draw."""
        return self._wire_line_string

    @property
    def start_arrow(self) -> Optional[Arrow]:
        """Arrow at the start of the line."""
        return self._start_arrow

    @property
    def end_arrow(self) -> Optional[Arrow]:
        """Arrow at the end of the line."""
        return self._end_arrow

    def _clip_start(self) -> None:
        """Clip the line at the start."""
        line = self._wire_line_string
        poly = self._start_polygon
        arrow: Optional[Arrow] = None
        attrs = self._wire.connection.attributes
        if attrs.arrow_back:
            arrow = Arrow(attrs)
        line = self._clip(line, poly, arrow, True)
        self._wire_line_string = line
        if arrow and arrow.is_valid():
            self._start_arrow = arrow

    def _clip_end(self) -> None:
        """Clip the line at the end."""
        line = self._wire_line_string
        poly = self._end_polygon
        arrow: Optional[Arrow] = None
        attrs = self._wire.connection.attributes
        if attrs.arrow_forward:
            arrow = Arrow(attrs)
        line = self._clip(line, poly, arrow, False)
        self._wire_line_string = line
        if arrow and arrow.geometry:
            self._end_arrow = arrow

    def _clip(
            self,
            line: LineString,
            poly: Polygon,
            arrow: Optional[Arrow] = None,
            start: bool = False,
    ) -> LineString:
        """Clip a line at the polygon.

        Returns the line for the wire.  If an arrow is given, it sets
        its polygon.  The 'start' argument tells whether the clipping
        is done at the start of the line or not.

        """
        # All calculations assume we work at the end of the line, so
        # reverse it if this not the case.
        if start:
            line = LineString(reversed(line.coords))
        # Clip the wire line at the boundary of the box.  This is the
        # final wire line if there is no arrow.
        line = line.difference(poly)
        if arrow:
            # There is an arrow at this end.
            arrow_length = arrow.length
            # The middle point of the arrow base is at a distance of
            # an arrow length from the box.
            poly1 = buffer_rectangle(poly, arrow_length)
            ls1 = line.difference(poly1)
            coords = ls1.coords
            if coords:
                # Set the geometry of the arrow.
                base_middle = ls1.coords[-1]
                tip = line.coords[-1]
                arrow.set_geometry(base_middle, tip)
                # Clip the line of the wire at *nearly* the distance
                # of an arrow length.  Make it a bit longer so that
                # the line and the arrow head do not appear
                # disconnected.
                poly2 = buffer_rectangle(poly, arrow_length - 1.0)
                line = line.difference(poly2)
            else:
                temp = "No room for arrow of connection '{}' -> '{}', omitted"
                connection = self._wire.connection
                msg = temp.format(connection.start.name, connection.end.name)
                log_warning(msg)
        # Do not forget to reverse the result if necessary.
        if start:
            line = LineString(reversed(line.coords))
        return line
