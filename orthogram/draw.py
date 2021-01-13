"""Draw a diagram layout as an image file.

This works in two steps: first you create a Drawing object for a
diagram Layout, then you use the write_svg() method to write the SVG
file.

Most calculations are performed during the initialization of the
Drawing object, which consists of the following steps:

1. A Track object is created for each axis of the layout.  There are
   horizontal and vertical tracks.

2. Lane objects are added to the tracks, each lane corresponding to an
   integer offset and containing one or more overlapping wire
   segments.  The width of the lane is calculated to be large enough
   for the thickest of the wires, the thickness of a wire being
   determined by the stroke width of the underlying connection.

3. The dimensions of the tracks are calculated using the width of the
   lanes and the distance between them as defined in the attributes of
   the diagram.

4. A BlockBox is created for each Block of the diagram and is
   associated with the tracks connected to it.  Each box starts out
   with minimal dimensions taken from its definition.  The initial
   dimensions are adjusted, if necessary, so that the box is large
   enough for the lanes connected to it.

5. Boxes behind other boxes are padded so that their edges remain
   visible.  The padding makes enough room for the label as well.

6. The dimensions of the tracks are recalculated taking into account
   the final dimensions of the boxes.

7. It is now possible to calculate the dimensions of the whole
   drawing.  A DiagramBox object is created, its bounds being the
   bounds of the drawing.

8. The absolute positions of the tracks and the bounds of the block
   boxes are calculated.

Drawing comes with its own set of challenges:

1. Markers.  They are employed to draw the arrows at the ends of the
   connections.  Arrow dimensions are rounded to integers.  A marker
   is created for each (width, length, color) combination and stored
   in a dictionary to be used for all the connections that match.

2. Box outlines.  In order to have accurate box dimensions, the
   outline is drawn just inside the box.  This means that both
   dimensions of the boxes in the SVG drawing are smaller by an amount
   equal to the width of the outline.

3. Clipping of lines.  Connection lines are drawn over boxes, so they
   must be clipped at both ends to make them look attached to the
   sides of the boxes (and not to the center of each box).  This
   becomes more complicated if there is an arrow at one end.  A buffer
   with an offset equal to the length of the arrow is created around
   the box and the line is clipped at its bounds.  The marker is
   placed in the middle between the end of the clipped line and the
   outline of the box.  The actual line drawn is made longer by a
   drawing unit, so that it does not appear disconnected from the base
   of the arrow.

4. Text.  This is the hardest problem of them all and no satisfactory
   solution has been found.  The program has no way to calculate the
   exact dimensions of a SVG text element.  That means that the
   dimensions of the boxes containing the text cannot be calculated;
   the program depends on the user providing sufficient values for the
   min_width and min_height attributes.  Positioning of text along the
   vertical axis is even more problematic.  The program assumes that
   the height of a line of text is text_line_height * font_size (both
   attributes redefinable by the user).  The default values seem to
   work well in Chrome and Inskape, but not in Firefox, at least with
   the default font settings.  Unfortunately, text always seems a bit
   off in Firefox.  In addition, redefining the label_distance
   attribute may be necessary when text is drawn near the edges of a
   box.

"""

import sys

from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from shapely.geometry import ( # type: ignore
    JOIN_STYLE,
    LineString,
    MultiPoint,
    Point,
    Polygon,
)

from svgwrite import Drawing as SvgDrawing # type: ignore
from svgwrite.container import Marker as SvgMarker # type: ignore

from .attributes import (
    ConnectionAttributes,
    ContainerAttributes,
    DiagramAttributes,
    TextAttributes,
)

from .diagram import (
    Block,
    Connection,
    Diagram,
    Node,
)

from .geometry import (
    Axis,
    Direction,
    IntPoint,
    FloatBounds,
    FloatPoint,
    Orientation,
    OrientedLine,
)

from .layout import (
    Layout,
    Network,
    Wire,
    WireSegment,
)

from .util import log_warning

######################################################################

class Lane:
    """Subdivision of a track, corresponds to an offset.

    Many overlapping wire segments may pass through a lane.

    """

    def __init__(self, name: str) -> None:
        """Initialize an empty lane.

        The name is used for debugging only and can be any string.

        """
        self._name = name
        self._relative_position = 0.0
        self._width = 0.0
        self._wires: List[Wire] = []

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({};relpos={},width={})".format(
            self.__class__.__name__,
            self._name,
            self._relative_position,
            self._width,
        )

    @property
    def relative_position(self) -> float:
        """Position of the lane relative to the axis of the track."""
        return self._relative_position

    @relative_position.setter
    def relative_position(self, value: float) -> None:
        self._relative_position = value

    @property
    def width(self) -> float:
        """Width of the lane."""
        return self._width

    def wires(self) -> Iterator[Wire]:
        """Return an iterator over the wires."""
        yield from self._wires

    def add_wire(self, wire: Wire) -> None:
        """Add a wire that runs through the lane."""
        wires = self._wires
        if wire in wires:
            return
        wires.append(wire)
        # Adapt the width of the lane to fit the new wire.
        width = wire.connection.attributes.stroke_width
        self._width = max(self._width, width)

######################################################################

class Track(OrientedLine):
    """Collection of parallel lanes running along one axis.

    The lanes are thought to run side by side along the track.  Each
    lane corresponds to an integer offset from the central axis.  Many
    overlapping wire segments may run through each lane.

    """

    def __init__(self, axis: Axis, attrs: DiagramAttributes):
        """Initialize an empty track running along a grid axis.

        The attributes of the diagram are needed to calculate the
        width of the track.

        """
        self._axis = axis
        self._name = axis.name
        self._diagram_attributes = attrs
        # Initial values for the empty track.
        self._rel_min = self._rel_max = 0.0
        self._position = 0.0
        self._lanes: Dict[int, Lane] = {}

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({};pos={},width={})".format(
            self.__class__.__name__,
            self._name,
            self._position,
            self.width,
        )

    @property
    def axis(self) -> Axis:
        """Axis on which the track lies."""
        return self._axis

    @property
    def width(self) -> float:
        """Width of the track."""
        return self._rel_max - self._rel_min

    @property
    def position(self) -> float:
        """Position of track in the drawing."""
        return self._position

    def position_with_offset(self, offset: int) -> float:
        """Return the position with the given offset.

        If the track does not contain any lanes, it is still possible
        to call this method as long as the offset is zero.  In that
        case the method returns the position of the track itself.

        """
        c = self._position
        lanes = self._lanes
        if not lanes:
            assert offset == 0
            return c
        else:
            lane = lanes[offset]
            return c + lane.relative_position

    def lanes(self) -> Sequence[Lane]:
        """Return an iterator over the lanes.

        The iterator provides the lanes according to their offsets.

        """
        lanes = self._lanes
        offsets = sorted(lanes.keys())
        result = []
        for offset in offsets:
            lane = lanes[offset]
            result.append(lane)
        return result

    def get_or_create_lane(self, offset: int) -> Lane:
        """Return the lane at the given offset.

        Creates a new lane if there is not one at the given offset.

        """
        track_name = self._name
        lanes = self._lanes
        lane = lanes.get(offset)
        if not lane:
            name = "{}.{}".format(track_name, offset)
            lane = Lane(name)
            lanes[offset] = lane
        return lane

    def update_for_lanes(self) -> None:
        """Update the geometry of the track so that it fits the lanes.

        This updates the relative positions of the lanes as well.

        """
        self._update_geometry_for_lanes()
        self._update_relative_positions_of_lanes()

    def _update_geometry_for_lanes(self) -> None:
        """Update the geometry of the track to fit the lanes."""
        lanes = self._lanes
        width = 0.0
        for lane in lanes.values():
            width += lane.width
        # Add the spaces between and around the lanes, only in case
        # there is at least one.
        if lanes:
            distance = self._diagram_attributes.connection_distance
            width += distance * (len(lanes) + 1)
        # Distribute width evenly around the axis.
        self._rel_min = -width / 2.0
        self._rel_max = width / 2.0

    def _update_relative_positions_of_lanes(self) -> None:
        """Calculate the positions of the lanes relative to the axis.

        This must be called after the geometry of the track due to the
        lanes has been calculated.

        """
        # Center the lanes around the axis.
        distance = self._diagram_attributes.connection_distance
        c = self._rel_min
        for lane in self.lanes():
            lane_width = lane.width
            c += distance + lane_width / 2.0
            lane.relative_position = c
            c += lane_width / 2.0

    def adjust_rel_min(self, value: float) -> None:
        """Adjust the minimum coordinate if given value is less."""
        self._rel_min = min(self._rel_min, value)

    def adjust_rel_max(self, value: float) -> None:
        """Adjust the maximum coordinate if given value is greater."""
        self._rel_max = max(self._rel_max, value)

    def update_position(self, base: float) -> None:
        """Update the position of the axis given the starting coordinate."""
        self._position = base + abs(self._rel_min)

######################################################################

class ContainerBox:
    """Box to draw for a container."""

    def __init__(
            self,
            attrs: ContainerAttributes,
            label: Optional[str] = None,
    ):
        """Initialize with attributes and label.

        If the label is None, the label from the attributes is used
        instead.

        """
        self._attributes = attrs
        if label is None:
            label = attrs.label
        self._label = label
        self._head_height = self._calculate_head_height()
        self._foot_height = self._calculate_foot_height()
        self._left_width = self._calculate_left_width()
        self._right_width = self._calculate_right_width()
        self._bounds: FloatBounds
        self._polygon: Polygon

    @property
    def attributes(self) -> ContainerAttributes:
        """Attributes of the box."""
        return self._attributes

    @property
    def label(self) -> Optional[str]:
        """Label of the box."""
        return self._label

    @property
    def head_height(self) -> float:
        """Height of the area over the contents."""
        return self._head_height

    @property
    def foot_height(self) -> float:
        """Height of the area under the contents."""
        return self._foot_height

    @property
    def left_width(self) -> float:
        """Width of the area left of the contents."""
        return self._left_width

    @property
    def right_width(self) -> float:
        """Width of the area right of the contents."""
        return self._right_width

    @property
    def bounds(self) -> FloatBounds:
        """Bounding box of the block box."""
        return self._bounds

    @bounds.setter
    def bounds(self, b: FloatBounds) -> None:
        self._bounds = b
        mp = MultiPoint([(b.xmin, b.ymin), (b.xmax, b.ymax)])
        self._polygon = mp.envelope

    @property
    def polygon(self) -> Polygon:
        """Polygon of the bounding box."""
        return self._polygon

    @property
    def central_point(self) -> FloatPoint:
        """Return the point at the center of the box.

        Note that this point is not necessarily on the intersection of
        the axes.

        """
        b = self._bounds
        x = (b.xmin + b.xmax) / 2.0
        y = (b.ymin + b.ymax) / 2.0
        return FloatPoint(x, y)

    def _calculate_head_height(self) -> float:
        """Calculate the height of the area over the contents."""
        attrs = self._attributes
        pad = attrs.stroke_width + attrs.padding_top
        if attrs.label_position.is_top():
            label = self._label
            pad += attrs.label_distance + _label_height(attrs, label)
        return pad

    def _calculate_foot_height(self) -> float:
        """Calculate the height of the area under the contents."""
        attrs = self._attributes
        pad = attrs.stroke_width + attrs.padding_bottom
        if attrs.label_position.is_bottom():
            label = self._label
            pad += attrs.label_distance + _label_height(attrs, label)
        return pad

    def _calculate_left_width(self) -> float:
        """Calculate the width of the area left of the contents."""
        attrs = self._attributes
        pad = attrs.stroke_width + attrs.padding_left
        return pad

    def _calculate_right_width(self) -> float:
        """Calculate the width of the area right of the contents."""
        attrs = self._attributes
        pad = attrs.stroke_width + attrs.padding_right
        return pad

######################################################################

class BlockBox(ContainerBox):
    """Box to draw for a block."""

    def __init__(
            self,
            block: Block,
            tracks: Iterable[Track],
            attrs: DiagramAttributes,
    ):
        """Initialize a box for the given block.

        Note that, in order to calculate the relative dimensions of
        the box, the geometry of the lanes in the tracks must have
        been already calculated.  The attributes of the diagram are
        needed in order to know the distance between the lanes.

        """
        ContainerBox.__init__(self, block.attributes, block.label())
        self._block = block
        self._diagram_attributes = attrs
        self._horizontal_tracks = self._pick_tracks(
            Orientation.HORIZONTAL, tracks
        )
        assert self._horizontal_tracks
        self._vertical_tracks = self._pick_tracks(
            Orientation.VERTICAL, tracks
        )
        assert self._vertical_tracks
        self._rel_xmin = self._calculate_rel_xmin()
        self._rel_ymin = self._calculate_rel_ymin()
        self._rel_xmax = self._calculate_rel_xmax()
        self._rel_ymax = self._calculate_rel_ymax()

    def __repr__(self) -> str:
        """Convert to string."""
        return "{}({};rxmin={},rymin={},rxmax={},rymax={})".format(
            self.__class__.__name__,
            self._block.name,
            self._rel_xmin,
            self._rel_ymin,
            self._rel_xmax,
            self._rel_ymax,
        )

    @property
    def block(self) -> Block:
        """Block for which the box has been created."""
        return self._block

    @property
    def rel_xmin(self) -> float:
        """Minimum horizontal coordinate relative to the axis."""
        return self._rel_xmin

    @property
    def rel_ymin(self) -> float:
        """Minimum vertical coordinate relative to the axis."""
        return self._rel_ymin

    @property
    def rel_xmax(self) -> float:
        """Maximum horizontal coordinate relative to the axis."""
        return self._rel_xmax

    @property
    def rel_ymax(self) -> float:
        """Maximum vertical coordinate relative to the axis."""
        return self._rel_ymax

    @property
    def track_bottom(self) -> Track:
        """Track at the bottom of the box."""
        return self._horizontal_tracks[-1]

    @property
    def track_left(self) -> Track:
        """Track at the left side of the box."""
        return self._vertical_tracks[0]

    @property
    def track_right(self) -> Track:
        """Track at the right side of the box."""
        return self._vertical_tracks[-1]

    @property
    def track_top(self) -> Track:
        """Track at the top of the box."""
        return self._horizontal_tracks[0]

    @staticmethod
    def _pick_tracks(
            ori: Orientation,
            tracks: Iterable[Track]
    ) -> List[Track]:
        """Return the tracks with the given orientation.

        The result is sorted by coordinate, so that it is easy to
        select the track at both ends (top, bottom etc).

        """
        def key(track: Track) -> int: return track.axis.coordinate
        result: List[Track] = []
        for track in tracks:
            if track.orientation is ori and track not in result:
                result.append(track)
        return sorted(result, key=key)

    def _calculate_rel_xmin(self) -> float:
        """Return the relative coordinate of the left side."""
        # Start with the minimum width of the block.
        block = self._block
        xmin = -block.attributes.min_width / 2.0
        # Adjust for the lanes of the leftmost track.
        track = self.track_left
        d = self._diagram_attributes.connection_distance
        for lane in track.lanes():
            x = lane.relative_position - (lane.width + d) / 2.0
            for wire in lane.wires():
                connection = wire.connection
                if (block is connection.start.block or
                    block is connection.end.block):
                    xmin = min(xmin, x)
        return xmin

    def _calculate_rel_ymin(self) -> float:
        """Return the relative coordinate of the top side."""
        # Start with the minimum height of the block.
        block = self._block
        ymin = -block.attributes.min_height / 2.0
        # Adjust for the lanes of the top track.
        track = self.track_top
        d = self._diagram_attributes.connection_distance
        for lane in track.lanes():
            y = lane.relative_position - (lane.width + d) / 2.0
            for wire in lane.wires():
                connection = wire.connection
                if (block is connection.start.block or
                    block is connection.end.block):
                    ymin = min(ymin, y)
        return ymin

    def _calculate_rel_xmax(self) -> float:
        """Return the relative coordinate of the right side."""
        # Start with the minimum width of the block.
        block = self._block
        xmax = block.attributes.min_width / 2.0
        # Adjust for the lanes of the rightmost track.
        track = self.track_right
        d = self._diagram_attributes.connection_distance
        for lane in track.lanes():
            x = lane.relative_position + (lane.width + d) / 2.0
            for wire in lane.wires():
                connection = wire.connection
                if (block is connection.start.block or
                    block is connection.end.block):
                    xmin = max(xmax, x)
        return xmax

    def _calculate_rel_ymax(self) -> float:
        """Return the relative coordinate of the bottom side."""
        # Start with the minimum height of the block.
        block = self._block
        ymax = block.attributes.min_height / 2.0
        # Adjust for the lanes of the bottom track.
        track = self.track_bottom
        d = self._diagram_attributes.connection_distance
        for lane in track.lanes():
            y = lane.relative_position + (lane.width + d) / 2.0
            for wire in lane.wires():
                connection = wire.connection
                if (block is connection.start.block or
                    block is connection.end.block):
                    ymax = max(ymax, y)
        return ymax

    def overlaps_with(self, other: 'BlockBox') -> bool:
        """True if this box overlaps with the other box."""
        return self._block.overlaps_with(other.block)

    def pad_top_from(self, y: float) -> None:
        """Pad box so that it is higher than the given coordinate."""
        y_new = y - self._head_height
        self._rel_ymin = min(self._rel_ymin, y_new)

    def pad_bottom_from(self, y: float) -> None:
        """Pad box so that it is lower than the given coordinate."""
        y_new = y + self._foot_height
        self._rel_ymax = max(self._rel_ymax, y_new)

    def pad_left_from(self, x: float) -> None:
        """Pad box so that it is to the left of the given coordinate."""
        x_new = x - self._left_width
        self._rel_xmin = min(self._rel_xmin, x_new)

    def pad_right_from(self, x: float) -> None:
        """Pad box so that it is to the right of the given coordinate."""
        x_new = x + self._right_width
        self._rel_xmax = max(self._rel_xmax, x_new)

    def update_tracks(self) -> None:
        """Update the geometry of the associated tracks."""
        attrs = self._block.attributes
        self.track_bottom.adjust_rel_max(self._rel_ymax + attrs.margin_bottom)
        self.track_left.adjust_rel_min(self._rel_xmin - attrs.margin_left)
        self.track_right.adjust_rel_max(self._rel_xmax + attrs.margin_right)
        self.track_top.adjust_rel_min(self._rel_ymin - attrs.margin_top)

    def update_bounds(self) -> None:
        """Calculate the bounds of the box and store them in it.

        The calculation depends on the positions of the associated
        tracks.

        """
        y1 = self.track_top.position + self._rel_ymin
        y2 = self.track_bottom.position + self._rel_ymax
        x1 = self.track_left.position + self._rel_xmin
        x2 = self.track_right.position + self._rel_xmax
        self.bounds = FloatBounds(x1, y1, x2, y2)

######################################################################

class WireLine:
    """Encapsulates the line string for a connection wire."""

    def __init__(
            self,
            wire: Wire,
            start_box: BlockBox,
            end_box: BlockBox,
            line_string: LineString,
    ):
        """Initialize for the given wire.

        The line string must be the one calculated directly from the
        positions of the tracks.  The boxes will be used to clip the
        line to its proper dimensions.

        """
        self._wire = wire
        self._start_box = start_box
        self._end_box = end_box
        self._wire_line_string = line_string
        self._start_marker_line_string: Optional[LineString] = None
        self._end_marker_line_string: Optional[LineString] = None
        self._clip_start()
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
    def start_marker_line_string(self) -> Optional[LineString]:
        """The line string for the arrow at the start."""
        return self._start_marker_line_string

    @property
    def end_marker_line_string(self) -> Optional[LineString]:
        """The line string for the arrow at the end."""
        return self._end_marker_line_string

    @property
    def polygons(self) -> Tuple[Polygon, Polygon]:
        """Polygons used to clip the line."""
        return (
            self._start_box.polygon,
            self._end_box.polygon,
        )

    def _clip_start(self) -> None:
        """Clip the line at the start."""
        ls = self._wire_line_string
        poly = self._start_box.polygon
        attrs = self._wire.connection.attributes
        arrow_length: Optional[float] = None
        if attrs.arrow_back:
            _, arrow_length = _arrow_dimensions(attrs)
        ls, ms = self._clip(ls, poly, arrow_length, True)
        self._wire_line_string = ls
        self._start_marker_line_string = ms

    def _clip_end(self) -> None:
        """Clip the line at the end."""
        ls = self._wire_line_string
        poly = self._end_box.polygon
        attrs = self._wire.connection.attributes
        arrow_length: Optional[float] = None
        if attrs.arrow_forward:
            _, arrow_length = _arrow_dimensions(attrs)
        ls, ms = self._clip(ls, poly, arrow_length, False)
        self._wire_line_string = ls
        self._end_marker_line_string = ms

    def _clip(
            self,
            ls: LineString,
            poly: Polygon,
            arrow_length: Optional[float] = None,
            start: bool = False,
    ) -> Tuple[LineString, Optional[LineString]]:
        """Clip a line at the polygon.

        Returns the line for the wire and, if an arrow length is
        given, a line for the marker.  The 'start' argument tells
        whether the clipping is done at the start of the line or not.

        """
        # All calculations assume we work at the end of the line, so
        # reverse it if this not the case.
        if start:
            ls = LineString(reversed(ls.coords))
        # Clip the wire line at the boundary of the box.  This is the
        # final wire line if there is no arrow marker.
        ls = ls.difference(poly)
        ms = None
        if arrow_length:
            # There is an arrow marker at this end.  The first point
            # of the marker line is at a distance of an arrow length
            # from the box.
            poly1 = _buffer(poly, arrow_length)
            ls1 = ls.difference(poly1)
            coords = ls1.coords
            if coords:
                p1 = ls1.coords[-1]
                # The second point of the marker line is at a distance of
                # half an arrow length from the box.
                poly2 = _buffer(poly, arrow_length / 2.0)
                ls2 = ls.difference(poly2)
                p2 = ls2.coords[-1]
                ms = LineString([p1, p2])
                # Clip the line of the wire at *nearly* the distance
                # of an arrow length.  Make it a bit longer so that
                # the line and the arrow marker do not appear
                # disconnected.
                poly3 = _buffer(poly, arrow_length - 1.0)
                ls = ls.difference(poly3)
            else:
                temp = "No room for arrow of connection '{}' -> '{}', omitted"
                connection = self._wire.connection
                msg = temp.format(connection.start.name, connection.end.name)
                log_warning(msg)
        # Do not forget to reverse the result if necessary.
        if start:
            ls = LineString(reversed(ls.coords))
        return ls, ms

######################################################################

class DiagramBox(ContainerBox):
    """Frame around the drawing."""

    def __init__(self, attrs: DiagramAttributes, tracks: Iterable[Track]):
        """Initialize for a diagram with the given attributes.

        It uses the tracks to calculate the dimensions of the drawing
        area; that means that the widths of the tracks must be already
        calculated.

        """
        ContainerBox.__init__(self, attrs)
        # Dimensions of the area needed for the objects.
        mw, mh = self._main_area_size(tracks)
        # Total dimensions of the drawing.
        hh = self._head_height
        fh = self._foot_height
        lw = self._left_width
        rw = self._right_width
        dw = lw + mw + rw
        dh = hh + mh + fh
        db = FloatBounds(0.0, 0.0, dw, dh)
        mb = FloatBounds(lw, hh, lw + mw, hh + mh)
        # Take into account lower limits.
        xw = attrs.min_width - dw
        if xw > 0.0:
            db.expand(xw, 0.0)
            mb.move(xw / 2.0, 0.0)
        xh = attrs.min_height - dh
        if xh > 0.0:
            db.expand(0.0, xh)
            mb.move(0.0, xh / 2.0)
        self.bounds = db
        self._main_area_bounds = mb

    @property
    def main_area_bounds(self) -> FloatBounds:
        """Bounding box of the main drawing area."""
        return self._main_area_bounds

    def _main_area_size(self, tracks: Iterable[Track]) -> Tuple[float, float]:
        """Calculate the dimensions of the main drawing area.

        Returns (width, height).

        """
        width = height = 0.0
        for track in set(tracks):
            if track.is_horizontal():
                height += track.width
            else:
                width += track.width
        return width, height

######################################################################

# Key for markers.  Depends on dimensions and color.
_MarkerKey = Tuple[int, int, str]

def _arrow_marker_key(width: int, length: int, stroke: str) -> _MarkerKey:
    """Return a key for the marker with the given attributes."""
    return width, length, stroke

# Mapping from marker keys to markers.
_Markers = Mapping[_MarkerKey, SvgMarker]

######################################################################

class Drawing:
    """Drawing of a diagram layout."""

    def __init__(self, layout: Layout):
        """Initialize the drawing of a layout."""
        self._layout = layout
        self._diagram = diagram = layout.diagram
        self._diagram_attributes = attrs = diagram.attributes
        self._tracks: Dict[Axis, Track] = {}
        self._init_tracks()
        self._add_lanes_to_tracks()
        self._block_boxes: Dict[Block, BlockBox] = {}
        self._init_boxes()
        self._pad_boxes()
        self._update_tracks_with_boxes()
        self._diagram_box = DiagramBox(attrs, self._tracks.values())
        self._update_track_positions()
        self._update_box_bounds()

    def _wires(self) -> Iterator[Wire]:
        """Return an iterator over the wires."""
        for net in self._layout.networks():
            yield from net.wires()

    def _ordered_block_boxes(self) -> Sequence[BlockBox]:
        """Return the boxes of the blocks.

        This method guarantees that the order of the boxes in the
        sequence corresponds to the order of the blocks in the
        diagram.

        """
        by_block = self._block_boxes
        boxes = []
        for block in self._diagram.blocks():
            # Blocks are not necessarily placed!
            box = by_block.get(block)
            if box:
                boxes.append(box)
        return boxes

    def _track(self, ori: Orientation, c: int) -> Track:
        """Return the track on the axis with the given values."""
        axis = Axis(ori, c)
        return self._tracks[axis]

    def _get_position(
            self,
            orientation: Orientation,
            coordinate: int,
            offset: Optional[int] = None,
    ) -> float:
        """Calculate the position for the given values."""
        axis = self._layout.grid.axis(orientation, coordinate)
        track = self._tracks[axis]
        if offset is None:
            return track.position
        else:
            return track.position_with_offset(offset)

    def _init_tracks(self) -> None:
        """Create the tracks of the drawing."""
        attrs = self._diagram_attributes
        tracks = self._tracks
        tracks.clear()
        for axis in self._layout.grid.axes():
            track = Track(axis, attrs)
            tracks[axis] = track

    def _add_lanes_to_tracks(self) -> None:
        """Create lanes for the wires and put them into their tracks."""
        tracks = self._tracks
        for wire in self._wires():
            for seg in wire.segments():
                axis = seg.axis
                track = tracks[axis]
                offset = seg.offset
                lane = track.get_or_create_lane(offset)
                lane.add_wire(wire)
        # We can now calculate the geometry of the tracks necessary
        # for the lanes at least.
        for track in tracks.values():
            track.update_for_lanes()

    def _init_boxes(self) -> None:
        """Create the boxes combining diagram and layout information.

        This must be called after the widths and the relative
        positions of the lanes have been calculated.

        """
        block_boxes = self._block_boxes
        block_boxes.clear()
        diagram = self._diagram
        for node, p in self._layout.nodes_and_points():
            for block in diagram.node_blocks(node):
                block_box = block_boxes.get(block)
                if not block_box:
                    block_box = self._create_block_box(block)
                    block_boxes[block] = block_box

    def _create_block_box(self, block: Block) -> BlockBox:
        """Create a new box for a block."""
        h = Orientation.HORIZONTAL
        v = Orientation.VERTICAL
        attrs = self._diagram.attributes
        layout = self._layout
        tracks: Set[Track] = set()
        for node in block.nodes():
            p = layout.node_point(node)
            track = self._track(h, p.i)
            tracks.add(track)
            track = self._track(v, p.j)
            tracks.add(track)
        box = BlockBox(block, tracks, attrs)
        return box

    def _update_tracks_with_boxes(self) -> None:
        """Updates the size of the tracks using the block boxes."""
        for box in self._block_boxes.values():
            box.update_tracks()

    def _pad_boxes(self) -> None:
        """Pad overlapping boxes.

        This method adds padding to the boxes that are behind other
        boxes (according to the drawing order), so that their borders
        and labels remain visible.  This affects the widths of the
        tracks as well.

        """
        boxes = list(self._ordered_block_boxes())
        boxes.reverse()
        for i, box1 in enumerate(boxes):
            bottom = box1.track_bottom
            left = box1.track_left
            right = box1.track_right
            top = box1.track_top
            for box2 in boxes[i + 1:]:
                if box1.overlaps_with(box2):
                    if box2.track_bottom is bottom:
                        box2.pad_bottom_from(box1.rel_ymax)
                    if box2.track_left is left:
                        box2.pad_left_from(box1.rel_xmin)
                    if box2.track_right is right:
                        box2.pad_right_from(box1.rel_xmax)
                    if box2.track_top is top:
                        box2.pad_top_from(box1.rel_ymin)

    def _update_track_positions(self) -> None:
        """Calculate the positions of the tracks and lanes.

        This must be called after the dimensions of the drawing have
        been calculated.

        """
        b = self._diagram_box.main_area_bounds
        x = b.xmin
        y = b.ymin
        for track in self._tracks.values():
            if track.is_horizontal():
                track.update_position(y)
                y += track.width
            else:
                track.update_position(x)
                x += track.width

    def _update_box_bounds(self) -> None:
        """Calculate the bounds of the block boxes.

        This must be called after the positions of the tracks have
        been calculated.

        """
        for box in self._block_boxes.values():
            box.update_bounds()

    def write_svg(self, filename: str) -> None:
        """Write the drawing to a SVG file."""
        extra = {}
        if self._diagram_attributes.stretch:
            # Set SVG dimensions to make it resizable.
            width, height = self._diagram_box.bounds.size
            extra['viewBox'] = "0 0 {} {}".format(width, height)
            extra['height'] = str(height)
        dwg = SvgDrawing(filename, **extra)
        self._draw_diagram_box(dwg)
        self._draw_block_boxes(dwg)
        markers = self._add_markers(dwg)
        self._draw_wires(dwg, markers)
        self._draw_block_labels(dwg)
        self._draw_diagram_label(dwg)
        dwg.save(pretty=True)

    def _draw_diagram_box(self, dwg: SvgDrawing) -> None:
        """Draw the box around the diagram."""
        self._draw_box(dwg, self._diagram_box)

    def _draw_diagram_label(self, dwg: SvgDrawing) -> None:
        """Draw the label (i.e. the title) of the diagram."""
        self._draw_box_label(dwg, self._diagram_box)

    def _draw_block_boxes(self, dwg: SvgDrawing) -> None:
        """Draw the boxes of the blocks."""
        for box in self._ordered_block_boxes():
            self._draw_box(dwg, box)

    def _draw_block_labels(self, dwg: SvgDrawing) -> None:
        """Draw the labels of the blocks."""
        for box in self._ordered_block_boxes():
            self._draw_box_label(dwg, box)

    @classmethod
    def _draw_box(cls, dwg: SvgDrawing, box: ContainerBox) -> None:
        """Draw a box."""
        bounds = box.bounds
        attrs = box.attributes
        # Draw the interior first.
        extra = {}
        fill = attrs.fill
        if fill:
            extra['fill'] = fill
        insert = (bounds.xmin, bounds.ymin)
        size = bounds.size
        rect = dwg.rect(insert=insert, size=size, **extra)
        dwg.add(rect)
        # Draw the outline over the interior, taking care that it
        # doesn't spill outside.
        stroke_width = attrs.stroke_width
        extra = {
            'stroke-width': str(stroke_width),
            'fill': 'none'
        }
        _maybe_add(extra, 'stroke', attrs.stroke)
        _maybe_add(extra, 'stroke-dasharray', attrs.stroke_dasharray)
        x = insert[0] + stroke_width / 2.0
        y = insert[1] + stroke_width / 2.0
        w = size[0] - stroke_width
        h = size[1] - stroke_width
        rect = dwg.rect(insert=(x, y), size=(w, h), **extra)
        dwg.add(rect)

    @classmethod
    def _draw_box_label(cls, dwg: SvgDrawing, box: ContainerBox) -> None:
        """Draw the label of a box."""
        label = box.label
        lines = _list_of_strings(label)
        if not lines:
            return
        bounds = box.bounds
        x1, y1 = bounds.xmin, bounds.ymin
        width, height = bounds.size
        attrs = box.attributes
        pos = attrs.label_position
        border = attrs.stroke_width
        label_height = _label_height(attrs)
        label_distance = attrs.label_distance
        d = border + label_distance + label_height / 2.0
        if pos.is_left():
            anchor = "start"
            x = x1 + border + label_distance
        elif pos.is_right():
            anchor = "end"
            x = x1 + width - border - label_distance
        else:
            anchor = "middle"
            x = x1 + width / 2.0
        if pos.is_top():
            y = y1 + d
        elif pos.is_bottom():
            y = y1 + height - d
        else:
            y = y1 + height / 2.0
        cls._draw_label(dwg, x, y, anchor, label, attrs)

    @classmethod
    def _draw_label(
            cls,
            dwg: SvgDrawing,
            x: float, y: float,
            anchor: str,
            label: Optional[str],
            attrs: TextAttributes,
    ) -> None:
        """Draw the label centered at the given point."""
        lines = _list_of_strings(label)
        if not lines:
            return
        # Place first line of text at the center.
        text = dwg.text("")
        text.translate(x, y)
        # Move text element up so the final element is centered
        # vertically.
        font_size = attrs.font_size
        line_height = attrs.text_line_height
        n_lines = len(lines)
        d = _pt_to_px(font_size) * 0.5 * line_height * (n_lines - 1)
        # Adjust for orientation.
        if attrs.text_orientation is Orientation.HORIZONTAL:
            text.translate(0, -d)
        if attrs.text_orientation is Orientation.VERTICAL:
            text.translate(-d, 0)
            text.rotate(-90)
        # Add lines as `tspan` elements inside the text.
        for i, line in enumerate(lines):
            kwargs = {
                'x': ["0"],
                'dx': ["0"],
                'font-family': attrs.font_family,
                'font-size': str(font_size) + "pt",
                'text-anchor': anchor,
                'dominant-baseline': 'middle',
            }
            _maybe_add(kwargs, 'fill', attrs.text_fill)
            _maybe_add(kwargs, 'font-style', attrs.font_style)
            _maybe_add(kwargs, 'font-weight', attrs.font_weight)
            if i > 0:
                kwargs['dy'] = [str(line_height) + "em"]
            tspan = dwg.tspan(line, **kwargs)
            text.add(tspan)
        dwg.add(text)

    def _add_markers(self, dwg: SvgDrawing) -> _Markers:
        """Add markers for the arrows of the wires to the drawing.

        It returns the markers so that they can be referenced by the
        wire elements.

        """
        markers = {}
        marker_extra = {
            'markerUnits': 'userSpaceOnUse',
            'orient': 'auto',
        }
        for wire in self._wires():
            attrs = wire.connection.attributes
            arrow_width, arrow_length = _arrow_dimensions(attrs)
            insert = (arrow_length / 2.0, arrow_width / 2.0)
            points = [
                (0, 0),
                (arrow_length, arrow_width / 2.0),
                (0, arrow_width),
            ]
            shape_extra = {
                'stroke-width': 0,
            }
            stroke = _str_or_empty(attrs.stroke)
            _maybe_add(shape_extra, 'fill', stroke)
            marker_key = _arrow_marker_key(arrow_width, arrow_length, stroke)
            if marker_key not in markers:
                marker = dwg.marker(
                    insert=insert,
                    size=(arrow_length, arrow_width),
                    **marker_extra
                )
                line = dwg.polyline(points, **shape_extra)
                marker.add(line)
                dwg.defs.add(marker)
                markers[marker_key] = marker
        return markers

    def _draw_wires(self, dwg: SvgDrawing, markers: _Markers) -> None:
        """Draw the wires."""
        for net in self._layout.networks():
            # Collect the lines necessary for the drawing.
            lines = []
            for wire in net.wires():
                line = self._wire_line(wire)
                lines.append(line)
            # Draw the background of the network to cover the other
            # lines drawn under it.
            for line in lines:
                self._draw_wire_buffer(dwg, line)
            # Draw the actual lines.
            for line in lines:
                # Draw the line.
                self._draw_wire_line(dwg, line)
                # Draw the markers.
                attrs = line.connection_attributes
                marker_line_strings = [
                    line.start_marker_line_string,
                    line.end_marker_line_string
                ]
                for ms in marker_line_strings:
                    if ms:
                        self._draw_marker(
                            dwg = dwg,
                            line_string = ms,
                            attrs = attrs,
                            markers = markers,
                        )

    def _wire_line(self, wire: Wire) -> WireLine:
        """Create a line between the two ends of the wire."""
        hor = Orientation.HORIZONTAL
        ver = Orientation.VERTICAL
        points = []
        for joint in wire.joints():
            p = joint.point
            h = joint.horizontal_offset
            v = joint.vertical_offset
            x = self._get_position(ver, p.j, h)
            y = self._get_position(hor, p.i, v)
            points.append((x, y))
        ls = LineString(points)
        boxes = self._block_boxes
        connection = wire.connection
        box1 = boxes[connection.start.block]
        box2 = boxes[connection.end.block]
        return WireLine(wire, box1, box2, ls)

    @staticmethod
    def _draw_wire_buffer(dwg: SvgDrawing, line: WireLine) -> None:
        """Draw the buffer of the wire."""
        attrs = line.connection_attributes
        stroke = attrs.buffer_fill
        if not stroke or stroke == "none":
            return
        b_width = attrs.buffer_width
        if not b_width:
            return
        width = attrs.stroke_width + 2 * b_width
        extra = {
            'stroke': stroke,
            'stroke-width': width,
            'fill': 'none',
        }
        ls = line.wire_line_string
        svg_line = dwg.polyline(ls.coords, **extra)
        dwg.add(svg_line)

    @classmethod
    def _draw_wire_line(cls, dwg: SvgDrawing, line: WireLine) -> None:
        """Draw the line of the wire."""
        attrs = line.connection_attributes
        width = attrs.stroke_width
        extra = {
            'stroke-width': width,
            'fill': 'none',
        }
        stroke = _str_or_empty(attrs.stroke)
        _maybe_add(extra, 'stroke', stroke)
        _maybe_add(extra, 'stroke-dasharray', attrs.stroke_dasharray)
        ls = line.wire_line_string
        svg_line = dwg.polyline(ls.coords, **extra)
        dwg.add(svg_line)

    @classmethod
    def _draw_marker(
            cls,
            dwg: SvgDrawing,
            line_string: LineString,
            attrs: ConnectionAttributes,
            markers: _Markers,
    ) -> None:
        """Draw the marker at one end of a wire."""
        # Draw an auxiliary line to the point of the arrow.
        svg_points = line_string.coords
        stroke = _str_or_empty(attrs.stroke)
        extra = {
            'stroke': stroke,
            'stroke-width': 0
        }
        svg_line = dwg.polyline(svg_points, **extra)
        dwg.add(svg_line)
        # Set the marker at the end of the auxiliary line.
        arrow_width, arrow_length = _arrow_dimensions(attrs)
        marker_key = _arrow_marker_key(arrow_width, arrow_length, stroke)
        marker = markers[marker_key]
        svg_line.set_markers([None, None, marker])

    def _pretty_print(self) -> None:
        """Print the drawing internals for debugging purposes."""
        print("Tracks:")
        for track in self._tracks.values():
            print("\t{}:".format(track))
            for lane in track.lanes():
                print("\t\t{}:".format(lane))
                for wire in lane.wires():
                    print("\t\t\t{}".format(wire))
        print("Block boxes:")
        for box in self._block_boxes.values():
            print("\t{}".format(box))

######################################################################

def _maybe_add(d: Dict[str, Any], name: str, value: Any) -> None:
    """Add the value to the dictionary if it is truthy."""
    if value:
        d[name] = value

def _str_or_empty(s: Optional[str]) -> str:
    """Returns the string itself or the empty one if None."""
    if s:
        return s
    else:
        return ""

def _list_of_strings(s: Optional[str]) -> List[str]:
    """Splits the string at newlines, returning a list."""
    if not s:
        return []
    else:
        return s.split("\n")

def _pt_to_px(pt: float) -> float:
    """Convert points to pixels (a.k.a. user units)."""
    return 1.25 * pt

def _label_height(attrs: TextAttributes, label: Optional[str] = None) -> float:
    """Calculate the height of the label.

    It uses the label in the attributes if an explicit label is not
    provided.

    """
    if not label:
        label = attrs.label
    lines = _list_of_strings(label)
    if lines:
        n_lines = len(lines)
        line_height = attrs.text_line_height
        font_size = attrs.font_size
        label_height = n_lines * line_height * _pt_to_px(font_size)
    else:
        label_height = 0.0
    return label_height

def _arrow_dimensions(attrs: ConnectionAttributes) -> Tuple[int, int]:
    """Return the dimensions of an arrow for a wire.

    The calculations are based on the width of the wire.  The result
    is (width, length).  The dimensions are rounded to the nearest
    integers to be better suited as marker keys.

    """
    width = attrs.stroke_width * attrs.arrow_base
    length = width * attrs.arrow_aspect
    return round(width), round(length)

def _buffer(poly: Polygon, distance: float) -> Polygon:
    """Creates a buffer around the polygon.

    This is supposed to be used with rectangular polygons.

    """
    return poly.buffer(distance, join_style=JOIN_STYLE.mitre)
