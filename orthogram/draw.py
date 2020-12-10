"""Draw a diagram layout as an image file."""

import sys

from enum import auto, Enum

from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
)

from shapely.geometry import ( # type: ignore
    LineString,
    Point,
    Polygon,
)

from shapely.ops import nearest_points # type: ignore

from svgwrite import Drawing as SvgDrawing # type: ignore
from svgwrite.container import Marker as SvgMarker # type: ignore

from .diagram import (
    DiagramAttributes,
    LabelPosition,
    Link,
    LinkAttributes,
    Node,
    TextAttributes,
)

from .geometry import (
    Direction,
    IntPoint,
    FloatPoint,
    Orientation,
    OrientedLine,
)

from .layout import (
    AxisLocation,
    Connector,
    ConnectorSegment,
    Layout,
    LayoutAxis,
    Network,
)

######################################################################

# Key for link markers.  Depends on stroke width and color.
MarkerKey = Tuple[int, str]

######################################################################

def _pt_to_px(pt: float) -> float:
    """Convert points to pixels (a.k.a. user units)."""
    return 1.25 * pt

######################################################################

class Box:
    """Box around a node."""

    def __init__(self, node: Node, point: IntPoint):
        """Initialize the box for the node at the given point."""
        self._node = node
        self._layout_point = point
        # These will be filled while drawing later on.
        self._central_point: FloatPoint
        self._width: float
        self._height: float
        self._polygon: Polygon

    @property
    def node(self) -> Node:
        """Diagram node inside the box."""
        return self._node
    
    @property
    def layout_point(self) -> IntPoint:
        """Position of the box in the layout."""
        return self._layout_point

    @property
    def width(self) -> float:
        """Width of the box."""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        self._width = value

    @property
    def height(self) -> float:
        """Height of the box."""
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        self._height = value

    @property
    def central_point(self) -> FloatPoint:
        """Center of the box in the drawing."""
        return self._central_point

    @central_point.setter
    def central_point(self, point: FloatPoint) -> None:
        self._central_point = point

    @property
    def polygon(self) -> Polygon:
        """Polygon drawn for the box."""
        return self._polygon

    @polygon.setter
    def polygon(self, poly: Polygon) -> None:
        self._polygon = poly

######################################################################

class Lane:
    """Subdivision of a track, corresponds to an offset.

    Many overlapping connectors may pass through a lane.

    """

    def __init__(self, offset: int):
        self._offset = offset
        self._connectors: Set[Connector] = set()
        self._width = 0.0
        self._position = 0.0

    def add_connector(self, connector: Connector) -> None:
        """Add a connector that runs through the lane."""
        self._connectors.add(connector)

    def connectors(self) -> Iterable[Connector]:
        """Return an iterator over the connectors."""
        return list(self._connectors)

    @property
    def width(self) -> float:
        """Width of the lane."""
        return self._width

    def calculate_width(self) -> None:
        """Calculate the width of the lane and store it in the instance.

        The lane must be wide enough for the thickest of the connector
        segments that run through it.

        """
        width = 0.0
        for conn in self._connectors:
            conn_width = conn.link.attributes.stroke_width
            width = max(width, conn_width)
        self._width = width

    @property
    def position(self) -> float:
        """Position of the lane in the drawing, in drawing units."""
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        self._position = value

    def __repr__(self) -> str:
        return "{}({};width={},position={})".format(
            self.__class__.__name__,
            self._offset,
            self._width,
            self._position,
        )

######################################################################

class Track(OrientedLine):
    """Collection of parallel lanes running along one axis.

    The lanes are thought to run side by side along the track.  Each
    lane corresponds to an integer offset from the central axis.  Many
    overlapping connectors may run through each lane.

    """

    def __init__(self, axis: LayoutAxis, attrs: DiagramAttributes):
        """Initialize an empty track running along a grid axis.

        The attributes of the diagram are needed to calculate the
        width of the track.

        """
        self._axis = axis
        self._diagram_attributes = attrs
        self._boxes: List[Box] = []
        self._lanes: Dict[int, Lane] = {}
        # Initial values for the empty track.
        self._lanes_width = 0.0
        self._width = 0.0
        self._position = 0.0

    @property
    def axis(self) -> LayoutAxis:
        """Axis on which the track lies."""
        return self._axis

    def add_box(self, box: Box) -> None:
        """Associate the box with the track."""
        boxes = self._boxes
        assert box not in boxes
        boxes.append(box)

    def boxes(self) -> Iterable[Box]:
        """Provide access to the boxes."""
        yield from self._boxes

    def get_lane(self, offset: int) -> Lane:
        """Return the lane at the given offset.

        Creates a new lane if there is not one already.

        """
        lanes = self._lanes
        lane = lanes.get(offset)
        if not lane:
            lane = Lane(offset)
            lanes[offset] = lane
        return lane

    def lanes(self) -> Sequence[Lane]:
        """Return the lanes of the track sorted by offset."""
        lanes = self._lanes
        offsets = sorted(lanes.keys())
        result = []
        for offset in offsets:
            lane = lanes[offset]
            result.append(lane)
        return result

    def calculate_width(self) -> None:
        """Calculate the width of the track and store it in the instance."""
        self._calculate_width_of_lanes()
        lanes_width = self._width_of_lanes()
        # Store the width of the lanes anyway, because we will need it
        # when we will be calculating their positions.
        self._lanes_width = lanes_width
        boxes_width = self._width_of_boxes()
        width = max(lanes_width, boxes_width)
        # We must also take into account the margins declared in the
        # attributes of the diagram.
        attrs = self._diagram_attributes
        location = self._axis.location
        if location is AxisLocation.OUTER_COLUMN:
            width += attrs.column_margin
        elif location is AxisLocation.OUTER_ROW:
            width += attrs.row_margin
        elif location is AxisLocation.COLUMN_BETWEEN_NODES:
            width += 2 * attrs.column_margin
        elif location is AxisLocation.ROW_BETWEEN_NODES:
            width += 2 * attrs.row_margin
        self._width = width

    def _calculate_width_of_lanes(self) -> None:
        """Tell the lanes to calculate their width."""
        for lane in self._lanes.values():
            lane.calculate_width()
            
    def _width_of_lanes(self) -> float:
        """Calculate the width necessary for the lanes."""
        lanes = self._lanes
        width = 0.0
        for lane in lanes.values():
            width += lane.width
        # Add the spaces between and around the lanes, only in case
        # there is at least one.
        if lanes:
            distance = self._diagram_attributes.link_distance
            width += distance * (len(lanes) + 1)
        return width

    def _width_of_boxes(self) -> float:
        """Calculate the width necessary for the boxes.

        The result does *not* include the margins around the boxes.

        """
        width = 0.0
        ori = self._axis.orientation
        for box in self._boxes:
            attrs = box.node.attributes
            if ori is Orientation.HORIZONTAL:
                box_width = attrs.min_height
            else:
                box_width = attrs.min_width
            width = max(width, box_width)
        return width

    @property
    def width(self) -> float:
        """Width of the track."""
        return self._width

    def calculate_position_starting_from(self, base: float) -> None:
        """Calculate the position of the track and store it.

        The track starts at the given base coordinate.  The position
        of the track is the coordinate of the central axis of the
        track, which lies halfway from the base.

        This method sets the positions of the lanes as well.

        """
        c = base + self._width / 2.0
        self._position = c
        # Calculate the position of the lanes, centering them around
        # the axis of the track.
        c -= self._lanes_width / 2.0
        distance = self._diagram_attributes.link_distance
        for lane in self.lanes():
            lane_width = lane.width
            c += distance + lane_width / 2.0
            lane.position = c
            c += lane_width / 2.0

    @property
    def position(self) -> float:
        """Position of track in the drawing."""
        return self._position

    def position_with_offset(self, offset: int) -> float:
        """Return the position with the given offset."""
        lane = self._lanes[offset]
        return lane.position

    def __repr__(self) -> str:
        return "{}({};width={},position={})".format(
            self.__class__.__name__,
            self._axis,
            self._width,
            self._position,
        )

######################################################################

class Drawing:
    """Drawing of a diagram layout."""

    # Fixed width/height aspect of the arrows.
    _arrow_aspect = 1.5

    def __init__(self, layout: Layout):
        """Initialize the drawing of a layout."""
        self._layout = layout
        self._diagram_attributes = layout.diagram.attributes
        self._boxes: Dict[Node, Box] = {}
        self._tracks: Dict[LayoutAxis, Track] = {}
        self._frame_size: Tuple[float, float] = (0.0, 0.0)
        #
        self._init_boxes()
        self._init_tracks()
        self._add_boxes_to_tracks()
        self._add_lanes_to_tracks()
        self._calculate_track_widths()
        self._calculate_track_positions()
        self._calculate_box_positions()
        self._calculate_box_dimensions()
        self._init_frame_size()

    def _init_boxes(self) -> None:
        """Create the boxes combining diagram and layout information."""
        boxes = self._boxes
        boxes.clear()
        for node, p in self._layout.nodes_and_points():
            box = Box(node, p)
            boxes[node] = box

    def _init_tracks(self) -> None:
        """Create the tracks of the drawing."""
        attrs = self._diagram_attributes
        tracks = self._tracks
        tracks.clear()
        for axis in self._layout.grid.axes():
            track = Track(axis, attrs)
            tracks[axis] = track

    def _add_boxes_to_tracks(self) -> None:
        """Associate the boxes of the nodes with the tracks."""
        tracks = self._tracks
        grid = self._layout.grid
        for box in self._boxes.values():
            p = box.layout_point
            axis = grid.axis(Orientation.HORIZONTAL, p.i)
            track = tracks[axis]
            track.add_box(box)
            axis = grid.axis(Orientation.VERTICAL, p.j)
            track = self._tracks[axis]
            track.add_box(box)

    def _add_lanes_to_tracks(self) -> None:
        """Construct lanes and put them in their tracks."""
        self._add_lanes_from_connectors()
        self._fix_tracks_without_connectors()

    def _add_lanes_from_connectors(self) -> None:
        """Add the lanes using the layout connectors.

        Note that there may be tracks with no connectors passing through
        them.  These are not covered by this method.

        """
        tracks = self._tracks
        for conn in self._connectors():
            for seg in conn.segments():
                axis = seg.axis
                track = tracks[axis]
                offset = seg.offset
                lane = track.get_lane(offset)
                lane.add_connector(conn)

    def _connectors(self) -> Iterator[Connector]:
        """Return an iterator over the connectors."""
        for net in self._layout.networks():
            yield from net.connectors()
            
    def _fix_tracks_without_connectors(self) -> None:
        """Add one empty lane to each track with no connectors through it.

        This is necessary in order to be able to get a coordinate out
        of the track.

        """
        for track in self._tracks.values():
            if not track.lanes():
                # This will create the lane.
                _ = track.get_lane(0)

    def _calculate_track_widths(self) -> None:
        """Calculate the widths of the tracks."""
        for track in self._tracks.values():
            track.calculate_width()

    def _calculate_track_positions(self) -> None:
        """Calculate the positions of the tracks."""
        x = self._main_area_x()
        y = self._main_area_y()
        for track in self._tracks.values():
            if track.is_horizontal():
                track.calculate_position_starting_from(y)
                y += track.width
            else:
                track.calculate_position_starting_from(x)
                x += track.width

    def _main_area_x(self) -> float:
        """Horizontal coordinate after which the tracks are drawn."""
        attrs = self._diagram_attributes
        border = attrs.stroke_width
        padding = attrs.padding
        return border + padding
        
    def _main_area_y(self) -> float:
        """Vertical coordinate after which the tracks are drawn."""
        attrs = self._diagram_attributes
        border = attrs.stroke_width
        padding = attrs.padding
        y = border + padding
        if attrs.label_position is LabelPosition.TOP:
            y += self._label_area_height()
        return y
        
    def _label_area_height(self) -> float:
        """Height of the area into which the label of the diagram is drawn.

        It is the sum of the height of the label and the distance from
        the border of the diagram.

        """
        attrs = self._diagram_attributes
        text = attrs.label
        distance = attrs.label_distance
        height = self._label_height(text, attrs)
        return distance + height
        
    def _label_height(
            self,
            label: Optional[str],
            attrs: TextAttributes
    ) -> float:
        """Calculate the height of the label according to the attributes."""
        lines = self._list_of_strings(label)
        if lines:
            n_lines = len(lines)
            line_height = attrs.text_line_height
            font_size = attrs.font_size
            label_height = n_lines * line_height * _pt_to_px(font_size)
        else:
            label_height = 0.0
        return label_height
        
    def _calculate_box_positions(self) -> None:
        """Calculate the positions of the boxes.

        It stores the positions inside the boxes themselves.

        """
        hor = Orientation.HORIZONTAL
        ver = Orientation.VERTICAL
        for box in self._boxes.values():
            p = box.layout_point
            x = self._get_position(ver, p.j)
            y = self._get_position(hor, p.i)
            c = FloatPoint(x, y)
            box.central_point = c
        
    def _calculate_box_dimensions(self) -> None:
        """Calculate the dimensions of the boxes.

        It stores the dimensions inside the boxes themselves.

        """
        Dir = Direction
        boxes = self._boxes
        # Initialize with default dimensions.
        for box in self._boxes.values():
            attrs = box.node.attributes
            box.width = attrs.min_width
            box.height = attrs.min_height
        # Find the segments connected to each box side.
        bds: Dict[Box, Dict[Direction, Set[ConnectorSegment]]] = {}
        for conn in self._connectors():
            for seg in conn.segments():
                joints = seg.joints()
                direc = seg.direction
                sides = []
                if direc is Dir.DOWN:
                    sides.append(Dir.DOWN)
                    sides.append(Dir.UP)
                elif direc is Dir.LEFT:
                    sides.append(Dir.LEFT)
                    sides.append(Dir.RIGHT)
                elif direc is Dir.RIGHT:
                    sides.append(Dir.RIGHT)
                    sides.append(Dir.LEFT)
                elif direc is Dir.UP:
                    sides.append(Dir.UP)
                    sides.append(Dir.DOWN)
                for i, side in enumerate(sides):
                    node = joints[i].node
                    if node:
                        box = boxes[node]
                        ds = bds.get(box)
                        if not ds:
                            ds = bds[box] = {}
                        s = ds.get(side)
                        if not s:
                            s = ds[side] = set()
                        s.add(seg)
        # Calculate the bounds for each side of each box.
        float_min = sys.float_info.min
        float_max = sys.float_info.max
        distance = self._diagram_attributes.link_distance
        tracks = self._tracks
        box_lengths: Dict[Box, Dict[Direction, Tuple[float, float]]] = {}
        for box, ds in bds.items():
            side_bounds = box_lengths.get(box)
            if not side_bounds:
                side_bounds = box_lengths[box] = {}
            for side, segments in ds.items():
                side_min = float_max
                side_max = float_min
                for seg in segments:
                    axis = seg.axis
                    track = tracks[axis]
                    offset = seg.offset
                    lane = track.get_lane(offset)
                    pos = lane.position
                    half = (lane.width + distance) / 2.0
                    seg_min = pos - half
                    seg_max = pos + half
                    side_min = min(side_min, seg_min)
                    side_max = max(side_max, seg_max)
                side_bounds[side] = (side_min, side_max)
        # Calculate the length for each side.
        reject = (float_max, float_min)
        for box, side_bounds in box_lengths.items():
            c = box.central_point
            hor_min = min(
                side_bounds.get(Dir.LEFT, reject)[0],
                side_bounds.get(Dir.RIGHT, reject)[0],
            )
            hor_max = max(
                side_bounds.get(Dir.LEFT, reject)[1],
                side_bounds.get(Dir.RIGHT, reject)[1],
            )
            ver_min = min(
                side_bounds.get(Dir.DOWN, reject)[0],
                side_bounds.get(Dir.UP, reject)[0],
            )
            ver_max = max(
                side_bounds.get(Dir.DOWN, reject)[1],
                side_bounds.get(Dir.UP, reject)[1],
            )
            if hor_min < hor_max:
                hor_length = 2.0 * max(abs(c.y - hor_min), abs(hor_max - c.y))
            else:
                hor_length = float_min
            if ver_min < ver_max:
                ver_length = 2.0 * max(abs(c.x - ver_min), abs(ver_max - c.x))
            else:
                ver_length = float_min
            box.width = max(ver_length, box.width)
            box.height = max(hor_length, box.height)
        
    def _init_frame_size(self) -> None:
        """Calculate the dimensions of the drawing.

        This is called after the dimensions of all the objects in the
        drawing have been calculated.

        """
        # Use the positions and widths stored in the tracks to
        # calculate where they end.
        x = y = 0.0
        for track in self._tracks.values():
            coord = track.position + track.width / 2.0
            if track.is_horizontal():
                y = max(y, coord)
            else:
                x = max(x, coord)
        # Borders left and right are symmetrical.
        width = x + self._main_area_x()
        # Add the height of the label if it is at the bottom.
        attrs = self._diagram_attributes
        if attrs.label_position is LabelPosition.BOTTOM:
            y += self._label_area_height()
        # Finish calculations with the border.
        border = attrs.stroke_width
        padding = attrs.padding
        height = y + padding + border
        # Take into account lower limits.
        width = max(width, attrs.min_width)
        height = max(height, attrs.min_height)
        self._frame_size = width, height

    def write_svg(self, filename: str) -> None:
        """Write the drawing to a SVG file."""
        extra = {}
        if self._diagram_attributes.stretch:
            # Set SVG dimensions to make it resizable.
            width, height = self._frame_size
            extra['viewBox'] = "0 0 {} {}".format(width, height)
            extra['height'] = str(height)
        dwg = SvgDrawing(filename, **extra)
        self._draw_diagram_frame(dwg)
        self._draw_nodes(dwg)
        markers = self._add_markers(dwg)
        self._draw_links(dwg, markers)
        self._draw_diagram_label(dwg)
        dwg.save(pretty=True)

    def _draw_diagram_frame(self, dwg: SvgDrawing) -> None:
        """Draw the frame around the diagram."""
        w, h = self._frame_size
        attrs = self._diagram_attributes
        # Draw the interior first.
        extra = {}
        fill = attrs.fill
        if fill:
            extra['fill'] = fill
        rect = dwg.rect(insert=(0, 0), size=(w, h), **extra)
        dwg.add(rect)
        # Draw the outline over the interior, taking care that it
        # doesn't spill outside.
        stroke_width = attrs.stroke_width
        extra = {
            'stroke-width': str(stroke_width),
            'fill': 'none'
        }
        self._maybe_add(extra, 'stroke', attrs.stroke)
        self._maybe_add(extra, 'stroke-dasharray', attrs.stroke_dasharray)
        insert = (stroke_width / 2.0, stroke_width / 2.0)
        size = (w - stroke_width, h - stroke_width)
        rect = dwg.rect(insert=insert, size=size, **extra)
        dwg.add(rect)
        
    def _draw_nodes(self, dwg: SvgDrawing) -> None:
        """Draw the nodes.

        This method updates the boxes around the nodes.  It sets their
        central points and stores the drawn polygons in them.

        """
        for box in self._boxes.values():
            self._draw_box(dwg, box)
            self._draw_node_label(dwg, box)

    def _draw_box(self, dwg: SvgDrawing, box: Box) -> None:
        """Draw the box around the node.

        It stores the polygon in the box.

        """
        c = box.central_point
        w = box.width
        h = box.height
        attrs = box.node.attributes
        stroke_width = attrs.stroke_width
        extra = {
            'stroke-width': stroke_width,
        }
        self._maybe_add(extra, 'stroke', attrs.stroke)
        self._maybe_add(extra, 'stroke-dasharray', attrs.stroke_dasharray)
        self._maybe_add(extra, 'fill', attrs.fill)
        x1 = c.x - w / 2.0
        y1 = c.y - h / 2.0
        rect = dwg.rect(insert=(x1, y1), size=(w, h), **extra)
        dwg.add(rect)
        # Try to make the clipping polygon a perfect fit, taking into
        # account the stroke width.
        d = stroke_width / 2.0
        points = [
            (x1 - d, y1 - d),
            (x1 + w + d, y1 - d),
            (x1 + w + d, y1 + h + d),
            (x1 - d, y1 + h + d)
        ]
        box.polygon = Polygon(points)

    def _draw_node_label(self, dwg: SvgDrawing, box: Box) -> None:
        """Draw the label of the node inside the box."""
        p = box.central_point
        node = box.node
        label = node.label()
        attrs = node.attributes
        self._draw_label(dwg, label, attrs, p.x, p.y)

    def _draw_label(
            self,
            dwg: SvgDrawing,
            label: Optional[str],
            attrs: TextAttributes,
            x: float, y: float,
    ) -> None:
        """Draw the label of a diagram element."""
        lines = self._list_of_strings(label)
        if not lines:
            return
        # Place first line of text at the center of the node.
        text = dwg.text("")
        text.translate(x, y)
        # Move text element up so the final element is centered
        # vertically.
        font_size = attrs.font_size
        line_height = attrs.text_line_height
        n_lines = len(lines)
        dy = -_pt_to_px(font_size) * 0.5 * line_height * (n_lines - 1)
        text.translate(0, dy)
        # Add lines as `tspan` elements inside the text.
        for i, line in enumerate(lines):
            kwargs = {
                'x': ["0"],
                'dx': ["0"],
                'font-family': attrs.font_family,
                'font-size': str(font_size) + "pt",
                'text-anchor': 'middle',
                'dominant-baseline': 'middle',
            }
            self._maybe_add(kwargs, 'fill', attrs.text_fill)
            self._maybe_add(kwargs, 'font-style', attrs.font_style)
            self._maybe_add(kwargs, 'font-weight', attrs.font_weight)
            if i > 0:
                kwargs['dy'] = [str(line_height) + "em"]
            tspan = dwg.tspan(line, **kwargs)
            text.add(tspan)
        dwg.add(text)

    def _add_markers(self, dwg: SvgDrawing) -> Mapping[MarkerKey, SvgMarker]:
        """Add markers for the arrows of the links to the drawing.

        It returns a dictionary of the markers so that they can be
        referenced by the link elements.

        """
        markers = {}
        marker_extra = {
            'markerUnits': 'userSpaceOnUse',
            'orient': 'auto',
        }
        distance = self._diagram_attributes.link_distance
        aspect = self._arrow_aspect
        for conn in self._connectors():
            attrs = conn.link.attributes
            width = attrs.stroke_width
            arrow_base, arrow_length = self._arrow_dimensions(width, distance)
            insert = (arrow_length / 2.0, arrow_base / 2.0)
            points = [
                (0, 0),
                (arrow_length, arrow_base / 2.0),
                (0, arrow_base),
            ]
            shape_extra = {
                'stroke-width': 0,
            }
            stroke = self._str_or_empty(attrs.stroke)
            self._maybe_add(shape_extra, 'fill', stroke)
            marker_key = self._arrow_marker_key(width, stroke)
            if marker_key not in markers:
                marker = dwg.marker(
                    insert=insert,
                    size=(arrow_length, arrow_base),
                    **marker_extra
                )
                line = dwg.polyline(points, **shape_extra)
                marker.add(line)
                dwg.defs.add(marker)
                markers[marker_key] = marker
        return markers

    def _arrow_dimensions(
            self,
            stroke_width: float,
            link_distance: float,
    ) -> Tuple[float, float]:
        """Return the dimensions of an arrow for a link.

        The calculations are based on the width of the link and the
        distance between the links.  The result is (base, length).

        """
        aspect = self._arrow_aspect
        base = stroke_width + link_distance
        length = aspect * base
        return base, length

    @staticmethod
    def _arrow_marker_key(width: float, stroke: str) -> MarkerKey:
        """Return a key for the marker with the given attributes."""
        # Round the width to the nearest integer; it is not a good
        # thing to use floats as keys.  The discrepancy in the drawing
        # should be minimal.
        return round(width), stroke

    def _draw_links(
            self,
            dwg: SvgDrawing,
            markers: Mapping[MarkerKey, SvgMarker],
    ) -> None:
        """Draw the links."""
        for net in self._ordered_networks():
            # Collect the data necessary for the drawing.
            data = []
            connectors = net.connectors()
            for conn in self._ordered_connectors(connectors):
                # Draw the line.
                whole_line = self._connector_line(conn)
                polygons = self._box_polygons(conn)
                attrs = conn.link.attributes
                clipped_line = self._clip_link_line(whole_line, attrs, polygons)
                datum = (clipped_line, attrs, polygons)
                data.append(datum)
            # Draw the background of the network to cover the other
            # the lines drawn under it.
            for line, attrs, polygons in data:
                self._draw_link_buffer(dwg, line, attrs)
            # Draw the actual lines.
            for line, attrs, polygons in data:
                # Draw the line.
                self._draw_link_line(dwg, line, attrs)
                # Draw the markers.
                stroke = self._str_or_empty(attrs.stroke)
                width = attrs.stroke_width
                cases = [
                    (attrs.arrow_back, 0),
                    (attrs.arrow_forward, -1)
                ]
                for do_draw, index in cases:
                    if do_draw:
                        self._draw_marker(
                            dwg = dwg,
                            link_point = Point(line.coords[index]),
                            box_polygon = polygons[index],
                            link_width = width,
                            link_stroke = stroke,
                            markers = markers,
                        )

    def _ordered_networks(self) -> Sequence[Network]:
        """Return the link networks ordered by drawing priority."""
        key = lambda net: net.drawing_priority()
        return sorted(self._layout.networks(), key=key)

    def _ordered_connectors(
            self, connectors: Iterable[Connector]
    ) -> Sequence[Connector]:
        """Return the connectors ordered by drawing priority."""
        key = lambda conn: conn.link.attributes.drawing_priority
        return sorted(connectors, key=key)

    def _connector_line(self, conn: Connector) -> LineString:
        """Create a line between the two ends of the connector."""
        hor = Orientation.HORIZONTAL
        ver = Orientation.VERTICAL
        points = []
        for joint in conn.joints():
            p = joint.point
            h = joint.horizontal_offset
            v = joint.vertical_offset
            x = self._get_position(ver, p.j, h)
            y = self._get_position(hor, p.i, v)
            points.append((x, y))
        return LineString(points)
        
    def _box_polygons(self, conn: Connector) -> Tuple[Polygon, Polygon]:
        """Return the polygons of the boxes at the two ends."""
        polygons = []
        boxes = self._boxes
        for joint in conn.joints():
            node = joint.node
            if node:
                box = boxes[node]
                polygons.append(box.polygon)
        assert len(polygons) == 2
        return polygons[0], polygons[1]
        
    def _clip_link_line(
            self,
            line: LineString,
            attrs: LinkAttributes,
            polygons: Tuple[Polygon, Polygon],
    ) -> LineString:
        """Clip the line of the link at the boundaries of the boxes.

        The polygons parameter consists of two polygons: one for the
        box at the first node of the link and one for the box at the
        last node.

        """
        link_distance = self._diagram_attributes.link_distance
        stroke_width = attrs.stroke_width
        back = attrs.arrow_back
        forward = attrs.arrow_forward
        _, arrow_length = self._arrow_dimensions(stroke_width, link_distance)
        polys = list(polygons)
        if back:
            polys[0] = polys[0].buffer(arrow_length)
        if forward:
            polys[1] = polys[1].buffer(arrow_length)
        for poly in polys:
            line = line.difference(poly)
        return line

    def _draw_link_buffer(
            self,
            dwg: SvgDrawing,
            line: LineString,
            attrs: LinkAttributes,
    ) -> None:
        """Draw the buffer of the link."""
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
        svg_line = dwg.polyline(line.coords, **extra)
        dwg.add(svg_line)

    def _draw_link_line(
            self,
            dwg: SvgDrawing,
            line: LineString,
            attrs: LinkAttributes,
    ) -> None:
        """Draw the line of the link."""
        width = attrs.stroke_width
        extra = {
            'stroke-width': width,
            'fill': 'none',
        }
        stroke = self._str_or_empty(attrs.stroke)
        self._maybe_add(extra, 'stroke', stroke)
        self._maybe_add(extra, 'stroke-dasharray', attrs.stroke_dasharray)
        svg_line = dwg.polyline(line.coords, **extra)
        dwg.add(svg_line)

    def _draw_marker(
            self,
            dwg: SvgDrawing,
            link_point: Point,
            box_polygon: Polygon,
            link_width: float,
            link_stroke: str,
            markers: Mapping[MarkerKey, SvgMarker],
    ) -> None:
        """Draw the marker at the end of a link."""
        # Find the point in the middle between the clipped line and
        # the polygon of the box.
        points = nearest_points(link_point, box_polygon)
        middle = LineString(points).interpolate(0.5, True)
        # Draw an auxiliary line ending at the middle point.
        svg_points = [
            (link_point.x, link_point.y),
            (middle.x, middle.y),
        ]
        extra = {
            'stroke': link_stroke,
            'stroke-width': 1
        }
        svg_line = dwg.polyline(svg_points, **extra)
        dwg.add(svg_line)
        # Set the marker at the end of the auxiliary line.
        marker_key = self._arrow_marker_key(link_width, link_stroke)
        marker = markers[marker_key]
        svg_line.set_markers([None, None, marker])

    def _draw_diagram_label(self, dwg: SvgDrawing) -> None:
        """Draw the label (i.e. the title) of the diagram."""
        attrs = self._diagram_attributes
        label = attrs.label
        lines = self._list_of_strings(label)
        if not lines:
            return
        width, height = self._frame_size
        x = width / 2.0
        border = attrs.stroke_width
        label_height = self._label_height(label, attrs)
        label_distance = attrs.label_distance
        dy = border + label_distance + label_height / 2.0
        if attrs.label_position is LabelPosition.TOP:
            y = dy
        else:
            y = height - dy
        self._draw_label(dwg, label, attrs, x, y)

    def _get_position(self,
                      orientation: Orientation,
                      coordinate: int,
                      offset: Optional[int] = None) -> float:
        """Calculate the position for the given values."""
        axis = self._layout.grid.axis(orientation, coordinate)
        track = self._tracks[axis]
        if offset is None:
            return track.position
        else:
            return track.position_with_offset(offset)

    @staticmethod
    def _list_of_strings(s: Optional[str]) -> List[str]:
        """Splits the string at newlines, returning a list."""
        if not s:
            return []
        else:
            return s.split("\n")
    
    @staticmethod
    def _str_or_empty(s: Optional[str]) -> str:
        """Returns the string itself or the empty one if None."""
        if s:
            return s
        else:
            return ""
        
    @staticmethod
    def _maybe_add(d: Dict[str, Any], name: str, value: Any) -> None:
        """Add the value to the dictionary if it is truthy."""
        if value:
            d[name] = value
        
    def _pretty_print(self) -> None:
        """Print the drawing internals for debugging purposes."""
        for track in self._tracks.values():
            print("{}:".format(track))
            for box in track.boxes():
                print("\t{}".format(box.node))
            for lane in track.lanes():
                print("\t{}:".format(lane))
                for conn in lane.connectors():
                    print("\t\t{}".format(conn))
